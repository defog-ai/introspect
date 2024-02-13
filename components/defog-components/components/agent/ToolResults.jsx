import { useCallback, useContext, useEffect, useMemo, useState } from "react";
import { reFormatData } from "../common/utils";
import { ReactiveVariablesContext } from "../../../docs/ReactiveVariablesContext";
import { ToolResultsTable } from "../ToolResultsTable";
import { ToolRunError } from "./ToolRunError";
import { ToolRunInputList } from "./ToolRunInputList";
import { ToolRunOutputList } from "./ToolRunOutputList";
import { ToolReRun } from "./ToolReRun";
import AgentLoader from "../common/AgentLoader";
import Lottie from "lottie-react";
import LoadingLottie from "../svg/loader.json";
import ErrorBoundary from "../common/ErrorBoundary";
import { csvParse } from "d3";
import { getToolRunData, toolDisplayNames } from "../../../../utils/utils";
import ToolRunAnalysis from "./ToolRunAnalysis";
import { AddStepUI } from "./AddStepUI";

function parseData(data_csv) {
  const data = csvParse(data_csv);
  const colNames = data.columns;
  const rows = data.map((d) => Object.values(d));

  const r = reFormatData(rows, colNames);

  return {
    columns: r.newCols,
    data: r.newRows,
  };
}

function parseOutputs(data, analysisData) {
  let parsedOutputs = {};
  // go through data and parse all tables
  Object.keys(data.outputs).forEach((k, i) => {
    parsedOutputs[k] = {};
    // check if this has data, reactive_vars and chart_images
    if (data.outputs[k].data) {
      parsedOutputs[k].data = parseData(data.outputs[k].data);
    }
    if (data.outputs[k].reactive_vars) {
      parsedOutputs[k].reactive_vars = data.outputs[k].reactive_vars;

      // check if title is defined
      if (!parsedOutputs[k]?.reactive_vars?.title) {
        Object.defineProperty(parsedOutputs[k].reactive_vars, "title", {
          get() {
            return analysisData?.user_question;
          },
        });
      }
    }
    if (data.outputs[k].chart_images) {
      parsedOutputs[k].chart_images = data.outputs[k].chart_images;
    }
    if (data.outputs[k].analysis) {
      parsedOutputs[k].analysis = data.outputs[k].analysis;
    }
  });
  return parsedOutputs;
}

export function ToolResults({
  analysisId,
  analysisData,
  activeNode,
  toolSocketManager = null,
  dag = null,
  setActiveNode = () => {},
  handleReRun = () => {},
  reRunningSteps = [],
  setPendingToolRunUpdates = () => {},
  toolRunDataCache = {},
  setToolRunDataCache = () => {},
}) {
  const [toolRunId, setToolRunId] = useState(null);
  const [toolRunData, setToolRunData] = useState(null);
  const [toolRunDataLoading, setToolRunDataLoading] = useState(false);
  const reactiveContext = useContext(ReactiveVariablesContext);
  const [edited, setEdited] = useState(false);

  const [parentNodeData, setParentNodeData] = useState({});

  const availableOutputNodes = useMemo(
    () => [...dag?.nodes()].filter((n) => !n.data.isTool),
    [dag]
  );

  const getNewData = useCallback(
    async (newId) => {
      if (!activeNode) return;
      setToolRunDataLoading(true);

      let res, newData;
      let hasCache = false;
      //   first find in context if available
      if (toolRunDataCache[newId]) {
        // use cache
        res = toolRunDataCache[newId];
        hasCache = true;
      } else {
        res = await getToolRunData(newId);
      }

      const newToolRunDataCache = { ...toolRunDataCache };

      if (res.success) {
        if (!hasCache) {
          // save to cache
          newToolRunDataCache[newId] = res;
        }

        // update reactive context
        Object.keys(res?.tool_run_data?.outputs || {}).forEach((k, i) => {
          if (!res?.tool_run_data?.outputs?.[k]?.reactive_vars) return;
          reactiveContext.update((prev) => {
            return {
              ...prev,
              [newId]: {
                ...prev[newId],
                [k]: res?.tool_run_data?.outputs?.[k]?.reactive_vars,
              },
            };
          });
        });

        // make life easier
        newData = res?.tool_run_data;

        newData.parsedOutputs = parseOutputs(newData, analysisData);
        // in case any of the inputs is a pd dataframe, we will also fetch those tool run's data

        const inputs = newData?.step?.inputs || [];

        let parentDfs = Array.from(
          inputs.reduce((acc, input, i) => {
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
          }, new Set())
        );

        // find nodes in the dag that have this output_storage_keys
        let parentNodes = availableOutputNodes.filter((n) => {
          return parentDfs.indexOf(n.data.id) > -1;
        });

        // get data for all these nodes using node.data.step.tool_run_id
        let parentIds = parentNodes.map((n) => n.data.step.tool_run_id);

        // get data for all these nodes
        let parentData = await Promise.all(
          parentIds.map((id) => {
            // try to get from cache
            if (toolRunDataCache[id]) {
              return toolRunDataCache[id];
            }
            return getToolRunData(id);
          })
        );

        // update toolRunDataCache
        parentData.forEach((d) => {
          if (d.success) {
            // parse outputs
            d.tool_run_data.parsedOutputs = parseOutputs(
              d.tool_run_data,
              analysisData
            );

            newToolRunDataCache[d.tool_run_data.tool_run_id] = d;
          }
        });

        setParentNodeData(
          parentData.reduce((acc, d) => {
            if (d.success) {
              acc[d.tool_run_data.tool_run_id] = d.tool_run_data;
            }
            return acc;
          }, {})
        );

        setToolRunId(newId);
        setToolRunData(newData);
        setEdited(newData.edited);
        setToolRunDataLoading(false);
      } else {
        setToolRunDataLoading(false);
        setToolRunData(res?.tool_run_data);
        if (!hasCache) {
          newToolRunDataCache[newId] = res;
        }

        // remove from reactive context
        reactiveContext.update((prev) => {
          const newContext = { ...prev };
          if (!newContext[newId]) return newContext;
          delete newContext[newId];
          return newContext;
        });
      }

      setToolRunDataCache((prev) => {
        return {
          ...prev,
          ...newToolRunDataCache,
        };
      });
    },
    [toolRunDataCache, reactiveContext, analysisData, activeNode]
  );

  function handleEdit({ analysis_id, tool_run_id, update_prop, new_val }) {
    if (!tool_run_id) return;
    if (!analysis_id) return;
    if (!update_prop) return;
    if (tool_run_id !== toolRunId) return;

    if (toolSocketManager && toolSocketManager.send) {
      // if sql, or code_str is present, they are in tool_run_details
      // update toolRunData and send to server
      toolSocketManager.send({
        analysis_id,
        tool_run_id,
        update_prop,
        new_val,
      });
      setEdited(true);
    }
    // edit this in the context too
    // but only do batch update when we click on another node
    // so we can prevent react rerendering
    setPendingToolRunUpdates((prev) => {
      return {
        [tool_run_id]: {
          ...prev[tool_run_id],
          [update_prop]: new_val,
        },
      };
    });
  }

  useEffect(() => {
    if (!activeNode || activeNode.data.isAddStepNode) return;

    async function getToolRun() {
      const toolRun = activeNode.data.isTool
        ? activeNode
        : [...activeNode?.parents()][0];
      const newId = toolRun?.data?.meta?.tool_run_id;

      if (!toolRun?.data?.isTool) {
        console.error(
          "Something's wrong on clicking node. No tool parents found."
        );
        console.log("Node clicked: ", activeNode);
      }

      await getNewData(newId);
    }

    getToolRun();
  }, [activeNode, reRunningSteps]);

  const isStepReRunning = reRunningSteps.indexOf(toolRunId) > -1;

  return !activeNode || !activeNode.data || !toolRunData ? (
    <></>
  ) : (
    <div className="tool-results-ctr" data-is-tool={activeNode.data.isTool}>
      {toolRunDataLoading || isStepReRunning ? (
        <div className="tool-run-loading">
          <AgentLoader
            message={toolRunDataLoading ? "Loading..." : "Tool re running..."}
            lottie={<Lottie animationData={LoadingLottie} loop={true} />}
          />
        </div>
      ) : activeNode && toolRunData && activeNode.data.isAddStepNode ? (
        <AddStepUI
          analysisId={analysisId}
          activeNode={activeNode}
          dag={dag}
          handleReRun={handleReRun}
        />
      ) : toolRunData?.error_message && !activeNode.data.isTool ? (
        <ToolRunError error_message={toolRunData?.error_message}></ToolRunError>
      ) : activeNode.data.isTool ? (
        <>
          <ErrorBoundary maybeOldAnalysis={true}>
            {toolRunData?.error_message && (
              <ToolRunError
                error_message={toolRunData?.error_message}
              ></ToolRunError>
            )}
            {edited && (
              <ToolReRun
                onClick={() => {
                  handleReRun(toolRunId);
                }}
              ></ToolReRun>
            )}
            <h1 className="tool-name">
              {toolDisplayNames[toolRunData.step.tool_name]}
            </h1>
            <h1 className="inputs-header">INPUTS</h1>
            <ToolRunInputList
              analysisId={analysisId}
              toolRunId={toolRunId}
              step={toolRunData.step}
              availableOutputNodes={availableOutputNodes}
              setActiveNode={setActiveNode}
              handleEdit={handleEdit}
              parentNodeData={parentNodeData}
            ></ToolRunInputList>
            <h1 className="details-header">OUTPUTS</h1>
            <ToolRunOutputList
              analysisId={analysisId}
              toolRunId={toolRunId}
              step={toolRunData.step}
              codeStr={toolRunData?.tool_run_details?.code_str}
              sql={toolRunData?.tool_run_details?.sql}
              handleEdit={handleEdit}
              availableOutputNodes={availableOutputNodes}
              setActiveNode={setActiveNode}
            ></ToolRunOutputList>
          </ErrorBoundary>
        </>
      ) : toolRunData?.parsedOutputs[activeNode.data.id] ? (
        <>
          <ToolResultsTable
            toolRunId={toolRunId}
            tableData={toolRunData?.parsedOutputs[activeNode.data.id]["data"]}
            chartImages={
              toolRunData?.parsedOutputs[activeNode.data.id]["chart_images"]
            }
            reactiveVars={
              toolRunData?.parsedOutputs[activeNode.data.id]["reactive_vars"]
            }
            nodeId={activeNode.data.id}
            analysisId={analysisId}
          />
          <div className="tool-run-analysis">
            <div className="tool-run-analysis-text">
              {toolRunData?.parsedOutputs[activeNode.data.id]["analysis"] ? (
                <p style={{ whiteSpace: "pre-wrap" }} className="small code">
                  {toolRunData?.parsedOutputs[activeNode.data.id]["analysis"]}
                </p>
              ) : (
                <ToolRunAnalysis
                  question={analysisData.user_question}
                  data_csv={toolRunData?.outputs[activeNode.data.id]["data"]}
                />
              )}
            </div>
          </div>
        </>
      ) : (
        <></>
      )}
    </div>
  );
}
