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
import { getToolRunData } from "../../../../utils/utils";
import ToolRunAnalysis from "./ToolRunAnalysis";

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
  const [isStepReRunning, setIsStepReRunning] = useState(false);

  const getNewData = useCallback(
    async (newId) => {
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

      console.log(res);

      if (res.success) {
        if (!hasCache) {
          // save to cache
          setToolRunDataCache((prev) => {
            return {
              ...prev,
              [newId]: res,
            };
          });
        }
      } else {
        setToolRunDataLoading(false);
        setToolRunData(res?.tool_run_data);
        if (!hasCache) {
          setToolRunDataCache((prev) => {
            return {
              ...prev,
              [newId]: res,
            };
          });
        }
        return;
      }

      // make life easier
      newData = res?.tool_run_data;

      newData.parsedOutputs = {};
      // go through newData and parse all tables
      Object.keys(newData.outputs).forEach((k, i) => {
        newData.parsedOutputs[k] = {};
        // check if this has data, reactive_vars and chart_images
        if (newData.outputs[k].data) {
          newData.parsedOutputs[k].data = parseData(newData.outputs[k].data);
        }
        if (newData.outputs[k].reactive_vars) {
          newData.parsedOutputs[k].reactive_vars =
            newData.outputs[k].reactive_vars;

          // check if title is defined
          if (!newData?.parsedOutputs[k]?.reactive_vars?.title) {
            Object.defineProperty(
              newData.parsedOutputs[k].reactive_vars,
              "title",
              {
                get() {
                  return analysisData?.user_question;
                },
              }
            );
            // update context
            reactiveContext.update((prev) => {
              return {
                ...prev,
                [newId]: {
                  ...prev[newId],
                  [k]: newData.parsedOutputs[k].reactive_vars,
                },
              };
            });
          }
        }
        if (newData.outputs[k].chart_images) {
          newData.parsedOutputs[k].chart_images =
            newData.outputs[k].chart_images;
        }
        if (newData.outputs[k].analysis) {
          newData.parsedOutputs[k].analysis = newData.outputs[k].analysis;
        }
      });

      // console.log("here", newData);

      setToolRunId(newId);
      setToolRunData(newData);
      setEdited(newData.edited);
      setToolRunDataLoading(false);
    },
    [toolRunDataCache, reactiveContext, analysisData]
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
    setPendingToolRunUpdates((prev) => {
      return {
        [tool_run_id]: {
          ...prev[tool_run_id],
          [update_prop]: new_val,
        },
      };
    });
  }

  const availableOutputNodes = useMemo(
    () => [...dag?.nodes()].filter((n) => !n.data.isTool),
    [dag]
  );

  useEffect(() => {
    if (!activeNode) return;

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

      // if (newId === toolRunId) return;
      await getNewData(newId);
    }

    getToolRun();
  }, [activeNode, reRunningSteps]);

  useEffect(() => {
    if (!toolRunId) return;

    if (toolRunId && reRunningSteps.indexOf(toolRunId) > -1) {
      setIsStepReRunning(true);
    } else {
      // if isStepReRunning is being changed from true to false
      // then get new data
      setIsStepReRunning(false);
    }
  }, [reRunningSteps]);

  return !activeNode || !activeNode.data ? (
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
      ) : (
        activeNode &&
        toolRunData &&
        (toolRunData.error_message && !activeNode.data.isTool ? (
          <ToolRunError
            error_message={toolRunData.error_message}
          ></ToolRunError>
        ) : activeNode.data.isTool ? (
          <>
            <ErrorBoundary maybeOldAnalysis={true}>
              {toolRunData.error_message && (
                <ToolRunError
                  error_message={toolRunData.error_message}
                ></ToolRunError>
              )}
              {edited && (
                <ToolReRun
                  onClick={() => {
                    handleReRun(toolRunId);
                  }}
                ></ToolReRun>
              )}
              <h1 className="tool-name">{toolRunData.step.tool_name}</h1>
              <h1 className="inputs-header">INPUTS</h1>
              <ToolRunInputList
                analysisId={analysisId}
                toolRunId={toolRunId}
                step={toolRunData.step}
                availableOutputNodes={availableOutputNodes}
                setActiveNode={setActiveNode}
                handleEdit={handleEdit}
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
            />
            <div className="tool-run-analysis">
              <p className="tool-run-analysis-header">ANALYSIS</p>
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
        ))
      )}
    </div>
  );
}
