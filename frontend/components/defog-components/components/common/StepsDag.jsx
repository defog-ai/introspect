import { useEffect, useMemo, useState } from "react";
import { HiWrenchScrewdriver } from "react-icons/hi2";
import { Popover } from "antd";
import { createDag } from "$utils/draw-dag";
import {
  PlusCircleFilled,
  PlusOutlined,
  PlusSquareFilled,
  PlusSquareOutlined,
  PlusSquareTwoTone,
} from "@ant-design/icons";
import { createInitialToolInputs, toolDisplayNames } from "$utils/utils";

const nodeCssSize = 15;

export default function StepsDag({
  steps,
  horizontal = false,
  nodeSize = [5, 5],
  nodeGap = null,
  activeNode = null,
  stageDone = true,
  reRunningSteps = [],
  dag = null,
  setDag = () => {},
  dagLinks = [],
  setDagLinks = () => {},
  setActiveNode = () => {},
  skipAddStepNode = false,
  setLastOutputNodeAsActive = true,
  disablePopovers = false,
  onPopoverOpenChange = () => {},
  alwaysShowPopover = false,
  toolIcon = () => <HiWrenchScrewdriver />,
  extraNodeClasses = () => "",
}) {
  const [graph, setGraph] = useState({ nodes: {}, links: [] });
  const [nodes, setNodes] = useState([]);
  const effectDep = JSON.stringify(steps || []);

  useEffect(() => {
    let g = { nodes: {}, links: [] };
    steps.forEach((step) => {
      // each step is a node
      // each resulting variable is a node
      // each input from global dictionaries is also node
      // if exists in nodes, don't do anything
      const step_id = step.tool_run_id;
      // create node for this step
      g["nodes"][step_id] = {
        id: step_id,
        title: step["tool_name"],
        key: step["tool_name"],
        isError: step.error_message,
        isTool: true,
        parents: new Set(),
        children: [],
        step: step,
      };

      // to find if this step could have parents, we will regex search for all matches for "global.*" in the inputs
      // and get unique parents
      let parents = Object.values(step["inputs"]).reduce((acc, input, i) => {
        let inp = input;
        // if input is a string, convert to array and do
        if (!Array.isArray(input)) {
          inp = [input];
        }

        inp.forEach((i) => {
          // if not a string don't do anything
          if (typeof i !== "string") return acc;

          let matches = [...i.matchAll(/(?:global_dict\.)(\w+)/g)];
          matches.forEach(([_, parent]) => {
            acc.add(parent);
          });
        });
        return acc;
      }, new Set());

      parents = Array.from(parents);

      parents.forEach((parent) => {
        // add a link from parent to child
        g["links"].push({
          source: parent,
          target: step_id,
        });

        // add this parent to the list of parents for this step
        g["nodes"][step_id]["parents"].add(parent);
        if (!g["nodes"][parent]) {
          console.log("Error: parent not found for step: ", step);
          console.log(parents, g["nodes"], step);
          return;
        }
        // add this step to the list of children for this parent
        g["nodes"][parent]["children"].push(g["nodes"][step_id]);
      });

      // convert set of parents to list
      g["nodes"][step_id]["parents"] = Array.from(
        g["nodes"][step_id]["parents"]
      );

      let children =
        step["outputs_storage_keys"] || step["result_storage_keys"];

      if (children) {
        children.forEach((child) => {
          // create nodes for each child
          if (!g["nodes"][child]) {
            g["nodes"][child] = {
              id: child,
              step: step,
              title: child,
              isTool: false,
              isOutput: true,
              isError: step.error_message,
              key: child,
              parents: [step_id],
              children: [],
            };
          }

          g["links"].push({
            source: step_id,
            target: child,
          });
          // add this child to the list of children for this step
          g["nodes"][step_id]["children"].push(g["nodes"][child]);

          if (!step.error_message && !skipAddStepNode) {
            // "add step" as a child of this child
            const addStepNodeId = child + "-add";

            // add a child that is basically a plus icon to add another node
            g["nodes"][addStepNodeId] = {
              id: addStepNodeId,
              isAddStepNode: true,
              title: "+",
              key: addStepNodeId,
              isTool: false,
              isError: step.error_message,
              parents: [child],
              children: [],
              step: {
                inputs: {},
                tool_name: null,
                parent_step: step,
              },
            };

            // also add a link
            g["links"].push({
              source: child,
              target: addStepNodeId,
            });
            g["nodes"][child]["children"].push(g["nodes"][addStepNodeId]);
          }
        });
      }

      // for each node, figure out it's "level"
      // level is the number of steps away from a node that has 0 parents
      // a node with 0 parents has level 0

      // go through each node, and go through it's parents
      Object.values(g["nodes"]).forEach((node) => {
        if (node["parents"].length == 0) node["level"] = 0;
        else {
          // find the parent with the highest level
          let highest_level = 0;
          node["parents"].forEach((parent_id) => {
            if (g["nodes"][parent_id]["level"] > highest_level)
              highest_level = g["nodes"][parent_id]["level"];
          });
          node["level"] = highest_level + 1;
        }
      });
    });

    const { dag, width, height } = createDag(
      Object.values(g["nodes"]).map((d) => ({
        ...d,
        parentIds: d.parents,
      })),
      nodeSize,
      nodeGap
    );

    dag.width = horizontal ? height : width;
    dag.height = horizontal ? width : height;

    const n = [...dag.nodes()];

    setGraph(g);
    setDag(dag);
    setDagLinks([...dag.links()]);
    setNodes(n);
    // also set active node to the leaf node
    try {
      // last step node as active
      const lastStep = steps?.[steps.length - 1];
      if (setLastOutputNodeAsActive) {
        // get the first output of this step
        const lastStepOutput = lastStep?.["outputs_storage_keys"]?.[0];
        const lastStepOutputNode = n?.find((d) => d.data.id === lastStepOutput);
        if (lastStepOutputNode) {
          setActiveNode(lastStepOutputNode);
        }
      } else {
        // set the first step as active
        const firstStep = steps?.[0];
        const firstStepNode = n?.find((d) => d.data.id === firstStep.id);
        if (firstStepNode) {
          setActiveNode(firstStepNode);
        }
      }
    } catch (e) {
      console.log("Error setting active node: ", e);
    }
  }, [effectDep]);

  return (
    <div className="analysis-graph" key={steps?.length}>
      {dag ? (
        <div className="graph" style={{ height: dag.height + 100 + "px" }}>
          {dag &&
            dag.nodes &&
            nodes.map((d) => {
              const extraProps = {};
              if (alwaysShowPopover) {
                extraProps.open = activeNode?.data?.id === d.data.id;
              }
              return (
                <Popover
                  {...extraProps}
                  onOpenChange={(visible) => onPopoverOpenChange(d, visible)}
                  rootClassName={
                    "graph-node-popover " +
                    (d.data.isError ? "popover-error " : "")
                  }
                  placement="left"
                  title={
                    !disablePopovers &&
                    (d?.data?.isAddStepNode
                      ? ""
                      : d?.data?.isTool
                        ? toolDisplayNames[d?.data?.step?.tool_name] || null
                        : `Output`)
                  }
                  content={
                    !disablePopovers &&
                    (d?.data?.isAddStepNode
                      ? "Create new step"
                      : d?.data?.isTool
                        ? d?.data?.step?.description || d.data.id
                        : null)
                  }
                  key={d.data.id}
                >
                  <div
                    className={
                      "graph-node" +
                      " " +
                      (d.data.isTool ? "tool" : "var") +
                      " " +
                      (d.data.isOutput ? " output" : "") +
                      " " +
                      (activeNode?.data?.id === d.data.id
                        ? "graph-node-active "
                        : "") +
                      (d.data.isError ? "graph-node-error" : "") +
                      " " +
                      `tool-run-${d.data.id}` +
                      " " +
                      (d.data.isAddStepNode ? "graph-node-add" : "") +
                      " " +
                      (reRunningSteps.some((s) => s.tool_run_id === d.data.id)
                        ? "graph-node-re-running"
                        : "") +
                      " " +
                      extraNodeClasses(d)
                    }
                    style={{
                      top: horizontal ? d.x : d.y,
                      left: horizontal
                        ? d.y
                        : d.x - (!d.data.isTool ? 0 : nodeSize[0] / 2),
                    }}
                    key={d.data.id}
                    onClick={() => {
                      setActiveNode(d);
                    }}
                  >
                    {d.data.isTool ? (
                      toolIcon(d)
                    ) : d.data.isAddStepNode ? (
                      <PlusSquareOutlined />
                    ) : (
                      <div className="graph-node-circle rounded-full w-4 h-4"></div>
                    )}
                  </div>
                </Popover>
              );
            })}
          <svg width={dag?.width + nodeCssSize} height={"100%"}>
            {dagLinks.map((d) => {
              // bezier curve
              const source = d.source;
              const target = d.target;
              const source_x =
                nodeCssSize / 2 + (horizontal ? source.y : source.x);
              const source_y = horizontal ? source.x : source.y + nodeCssSize;
              const target_x =
                nodeCssSize / 2 + (horizontal ? target.y : target.x);
              const target_y = horizontal ? target.x : target.y;
              let pathData = `M ${source_x} ${source_y} L ${target_x} ${target_y}`;

              return (
                <path
                  className={
                    "link" +
                    " " +
                    (target.data.isAddStepNode ? "link-add-node" : "")
                  }
                  id={source.data.id + "-" + target.data.id}
                  d={pathData}
                  stroke="black"
                  fill="none"
                  key={source.data.id + " - " + target.data.id + "-" + pathData}
                />
              );
            })}
          </svg>
          {!stageDone ? (
            // get one of the leafs of the dag and place a loading icon 20 px below it
            dag && dag.leaves && [...dag.leaves()].length > 0 ? (
              <>
                <div className="graph-node-loading">
                  <div
                    className="graph-node-loading-icon"
                    style={{
                      top: horizontal
                        ? [...dag.leaves()][0].x + nodeCssSize
                        : [...dag.leaves()][0].y + nodeCssSize + 10,
                      left: horizontal
                        ? [...dag.leaves()][0].y
                        : [...dag.leaves()][0].x,
                    }}
                  ></div>
                </div>
              </>
            ) : (
              <></>
            )
          ) : (
            <></>
          )}
        </div>
      ) : (
        <></>
      )}
    </div>
  );
}
