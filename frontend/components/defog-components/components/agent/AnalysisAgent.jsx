import React, {
  useEffect,
  useRef,
  useState,
  Fragment,
  useContext,
  useCallback,
  useMemo,
  useSyncExternalStore,
} from "react";
import { ThemeContext, lightThemeColor } from "../../context/ThemeContext";
import AgentLoader from "../common/AgentLoader";
import Lottie from "lottie-react";
import LoadingLottie from "../svg/loader.json";
import { DocContext } from "../../../docs/DocContext";
import { ToolResults } from "./ToolResults";
import StepsDag from "../common/StepsDag";
import ErrorBoundary from "../common/ErrorBoundary";
import { Context } from "$components/common/Context";
import { toolShortNames, trimStringToLength } from "$utils/utils";
import { ReactiveVariablesContext } from "../../../docs/ReactiveVariablesContext";
import Input from "antd/es/input";
import Clarify from "./analysis-gen/Clarify";
import AnalysisManager from "./analysisManager";
import setupBaseUrl from "$utils/setupBaseUrl";
import { AnalysisFeedback } from "./feedback/AnalysisFeedback";
import { MessageManagerContext } from "$components/tailwind/Message";

const getToolsEndpoint = setupBaseUrl("http", "get_user_tools");

export const AnalysisAgent = ({
  analysisId,
  token,
  keyName,
  devMode,
  didUploadFile,
  editor,
  block,
  createAnalysisRequestBody = {},
  initiateAutoSubmit = false,
  searchRef = null,
  setGlobalLoading = (...args) => {},
  onManagerCreated = (...args) => {},
  onManagerDestroyed = (...args) => {},
}) => {
  // const [messageApi, contextHolder] = message.useMessage();
  console.log("Key name", keyName);
  console.log("Did upload file", didUploadFile);
  const [pendingToolRunUpdates, setPendingToolRunUpdates] = useState({});
  const [reRunningSteps, setRerunningSteps] = useState([]);
  const reactiveContext = useContext(ReactiveVariablesContext);
  const [context, setContext] = useContext(Context);
  const { user } = context;
  const [activeNode, setActiveNodePrivate] = useState(null);
  const [dag, setDag] = useState(null);
  const [dagLinks, setDagLinks] = useState([]);
  // in case this isn't called from analysis version viewer (which has a central singular search bar)
  // we will have an independent search bar for each analysis as well
  const independentAnalysisSearchRef = useRef();
  const [toolRunDataCache, setToolRunDataCache] = useState({});
  const [tools, setTools] = useState({});

  const docContext = useContext(DocContext);

  const messageManager = useContext(MessageManagerContext);

  const { mainManager, reRunManager, toolSocketManager } =
    docContext.val.socketManagers;

  function onMainSocketMessage(response, newAnalysisData) {
    try {
      if (response.error_message) {
        // messageManager.error(response.error_message);
        throw new Error(response.error_message);
      }
      setToolRunDataCache(analysisManager.toolRunDataCache);

      if (response && response?.done) {
        setAnalysisBusy(false);
        setGlobalLoading(false);
      }

      if (newAnalysisData) {
        // if current stage is clarify
        // but clarification steps length is 0
        // submit again
        if (
          newAnalysisData.currentStage === "clarify" &&
          !newAnalysisData?.clarify?.clarification_questions?.length
        ) {
          handleSubmit(
            newAnalysisData.user_question,
            { clarification_questions: [] },
            null
          );
        }
      }
    } catch (e) {
      messageManager.error(e);
      console.log(e);
      setAnalysisBusy(false);
      setGlobalLoading(false);
    }
  }

  const onReRunMessage = useCallback(
    (response) => {
      try {
        setRerunningSteps(analysisManager.reRunningSteps);
        // remove all pending updates for this tool_run_id
        // because all new data is already there in the received response
        setPendingToolRunUpdates((prev) => {
          const newUpdates = { ...prev };
          delete newUpdates[response.tool_run_id];
          return newUpdates;
        });

        setToolRunDataCache(analysisManager.toolRunDataCache);

        // and set active node to this one
        const parentNodes = [...dag.nodes()].filter(
          (d) =>
            d.data.isOutput &&
            d.data.parentIds.find((p) => p === response.tool_run_id)
        );
        if (parentNodes.length) {
          setActiveNodePrivate(parentNodes[0]);
        }

        if (response.error_message) {
          // messageManager.error(response.error_message);
          throw new Error(response.error_message);
        }

        // update reactive context
        Object.keys(response?.tool_run_data?.outputs || {}).forEach((k, i) => {
          if (!response?.tool_run_data?.outputs?.[k]?.reactive_vars) return;
          const runId = response.tool_run_id;
          reactiveContext.update((prev) => {
            return {
              ...prev,
              [runId]: {
                ...prev[runId],
                [k]: response?.tool_run_data?.outputs?.[k]?.reactive_vars,
              },
            };
          });
        });
      } catch (e) {
        messageManager.error(e);
        console.log(e.stack);
      } finally {
        setAnalysisBusy(false);
        setGlobalLoading(false);
      }
    },
    [dag]
  );

  const analysisManager = useMemo(() => {
    return AnalysisManager({
      analysisId,
      onNewData: onMainSocketMessage,
      onReRunData: onReRunMessage,
      token,
      didUploadFile,
      keyName,
      devMode,
      userEmail: user,
      createAnalysisRequestBody,
    });
  }, [analysisId]);

  analysisManager.setOnReRunDataCallback(onReRunMessage);

  const [analysisBusy, setAnalysisBusy] = useState(initiateAutoSubmit);

  const analysisData = useSyncExternalStore(
    analysisManager.subscribeToDataChanges,
    analysisManager.getAnalysisData
  );

  function setActiveNode(node) {
    setActiveNodePrivate(node);
    // if update_prop is "sql" or "code_str" or "analysis", update tool_run_details
    // if update_prop is inputs, update step.inputs
    // update in context
    Object.keys(pendingToolRunUpdates).forEach((toolRunId) => {
      const updateProps = Object.keys(pendingToolRunUpdates[toolRunId]);
      const toolRunData = toolRunDataCache[toolRunId]?.tool_run_data;
      if (!toolRunData) return;

      updateProps.forEach((updateProp) => {
        if (updateProp === "sql" || updateProp === "code_str") {
          // update tool_run_details
          toolRunData.tool_run_details[updateProp] =
            pendingToolRunUpdates[toolRunId][updateProp];
        } else if (updateProp === "inputs") {
          // update step.inputs
          toolRunData.step.inputs =
            pendingToolRunUpdates[toolRunId][updateProp];
        }
      });
      toolRunData.edited = true;

      // update the cache
      setToolRunDataCache((prev) => {
        return {
          ...prev,
          [toolRunId]: {
            ...prev[toolRunId],
            tool_run_data: toolRunData,
          },
        };
      });
    });

    setPendingToolRunUpdates({});
  }

  useEffect(() => {
    async function initialiseAnalysis() {
      try {
        await analysisManager.init();

        const response = await fetch(getToolsEndpoint, {
          method: "POST",
        });

        const tools = (await response.json())["tools"];
        setTools(tools);

        if (analysisManager.wasNewAnalysisCreated) {
          // also have to set docContext in this case
          docContext.update({
            ...docContext.val,
            userItems: {
              ...docContext.val.userItems,
              analyses: [...docContext.val.userItems.analyses, analysisId],
            },
          });
        }
        if (
          initiateAutoSubmit &&
          !analysisManager?.analysisData?.currentStage
        ) {
          handleSubmit(analysisManager?.analysisData?.user_question, {}, null);
        } else {
          setAnalysisBusy(false);
        }
      } catch (e) {
        messageManager.error(e);
        console.log(e.stack);
      }
    }
    initialiseAnalysis();
  }, []);

  useEffect(() => {
    if (analysisManager) {
      onManagerCreated(analysisManager, analysisId);
      if (mainManager && reRunManager) {
        analysisManager.setMainSocket(mainManager);
        analysisManager.setReRunSocket(reRunManager);

        analysisManager.addEventListeners();

        return () => {
          analysisManager.removeEventListeners();
        };
      }
    }
  }, [analysisManager, mainManager, reRunManager]);

  const handleSubmit = useCallback(
    (query, stageInput = {}, submitStage = null) => {
      try {
        if (!query) throw new Error("Query is empty");
        analysisManager.submit(query, stageInput, submitStage);
        setAnalysisBusy(true);
        setGlobalLoading(true);
      } catch (e) {
        messageManager.error(e);
        console.log(e.stack);
        setAnalysisBusy(false);
        setGlobalLoading(false);
        // if the current stage is null, just destroy this analysis
        if (submitStage === null) {
          analysisManager.destroy();
          onManagerDestroyed(analysisManager, analysisId);
        }
      }
    },
    [analysisManager, setGlobalLoading]
  );
  const handleReRun = useCallback(
    (toolRunId, preRunActions = {}) => {
      if (
        !toolRunId ||
        !dag ||
        !analysisId ||
        !reRunManager ||
        !reRunManager.send ||
        !activeNode
      ) {
        console.log(toolRunId, dag, analysisId, reRunManager, activeNode);
        return;
      }

      try {
        analysisManager.initiateReRun(toolRunId, preRunActions);
      } catch (e) {
        messageManager.error(e);
        console.log(e.stack);
      }
    },
    [analysisId, activeNode, reRunManager, dag, analysisManager]
  );

  return (
    <ErrorBoundary>
      <div className="analysis-agent-container min-h-96 mr-4 p-4 border rounded-md">
        <ThemeContext.Provider
          value={{ theme: { type: "light", config: lightThemeColor } }}
          key="1"
        >
          {!analysisData ? (
            <div className="analysis-data-loader">
              <AgentLoader
                message={"Setting up..."}
                lottie={<Lottie animationData={LoadingLottie} loop={true} />}
              />
            </div>
          ) : (
            <div className="analysis-ctr">
              {!searchRef && !analysisData.currentStage ? (
                <div className="">
                  <Input
                    type="text"
                    ref={independentAnalysisSearchRef}
                    onPressEnter={(ev) => {
                      handleSubmit(ev.target.value);
                    }}
                    placeholder="Ask a question"
                    disabled={analysisBusy}
                    rootClassName="bg-white mx-auto left-0 right-0 border-2 border-gray-400  p-2 rounded-lg w-full lg:w-6/12 mx-auto h-16 shadow-custom hover:border-blue-500 focus:border-blue-500"
                  />
                </div>
              ) : (
                <></>
              )}
              {analysisData.currentStage === "clarify" ? (
                <div className="analysis-recipe w-full">
                  <Clarify
                    data={analysisData.clarify}
                    handleSubmit={(stageInput, submitStage) => {
                      handleSubmit(
                        analysisData?.user_question,
                        stageInput,
                        submitStage
                      );
                    }}
                    globalLoading={analysisBusy}
                    stageDone={
                      analysisData.currentStage === "clarify"
                        ? !analysisBusy
                        : true
                    }
                    isCurrentStage={analysisData.currentStage === "clarify"}
                  />
                </div>
              ) : (
                <></>
              )}

              {analysisData.currentStage === "gen_steps" ? (
                <div className="analysis-content flex flex-row max-w-full">
                  <div className="analysis-results flex flex-col grow basis-0 overflow-scroll relative">
                    <ErrorBoundary>
                      {analysisData?.gen_steps?.steps.length ? (
                        <>
                          {!analysisBusy && analysisData && (
                            <div className="basis-0">
                              <AnalysisFeedback
                                analysisSteps={
                                  analysisData?.gen_steps?.steps || []
                                }
                                analysisId={analysisId}
                                user_question={analysisData?.user_question}
                                token={token}
                                keyName={keyName}
                              />
                            </div>
                          )}
                          <div className="basis-0 grow flex place-content-start">
                            <ToolResults
                              analysisId={analysisId}
                              activeNode={activeNode}
                              analysisData={analysisData}
                              toolSocketManager={toolSocketManager}
                              dag={dag}
                              setActiveNode={setActiveNode}
                              handleReRun={handleReRun}
                              reRunningSteps={reRunningSteps}
                              setPendingToolRunUpdates={
                                setPendingToolRunUpdates
                              }
                              toolRunDataCache={toolRunDataCache}
                              setToolRunDataCache={setToolRunDataCache}
                              tools={tools}
                              analysisBusy={analysisBusy}
                              handleDeleteSteps={async (toolRunIds) => {
                                try {
                                  await analysisManager.deleteSteps(toolRunIds);
                                } catch (e) {
                                  messageManager.error(e);
                                  console.log(e.stack);
                                }
                              }}
                            ></ToolResults>
                          </div>
                        </>
                      ) : (
                        analysisBusy && (
                          <AgentLoader
                            message={
                              analysisData.currentStage === "gen_steps"
                                ? "Generating SQL..."
                                : "Executing plan..."
                            }
                            lottie={
                              <Lottie
                                animationData={LoadingLottie}
                                loop={true}
                              />
                            }
                          />
                        )
                      )}
                    </ErrorBoundary>
                  </div>
                  <div className="analysis-steps basis-0">
                    <StepsDag
                      steps={analysisData?.gen_steps?.steps || []}
                      nodeSize={[40, 10]}
                      nodeGap={[30, 50]}
                      setActiveNode={setActiveNode}
                      reRunningSteps={reRunningSteps}
                      activeNode={activeNode}
                      stageDone={
                        analysisData.currentStage === "gen_steps"
                          ? !analysisBusy
                          : true
                      }
                      dag={dag}
                      setDag={setDag}
                      dagLinks={dagLinks}
                      setDagLinks={setDagLinks}
                      extraNodeClasses={(node) => {
                        return node.data.isTool
                          ? `rounded-md px-1 text-center`
                          : "";
                      }}
                      toolIcon={(node) => (
                        <p className="text-sm truncate m-0">
                          {trimStringToLength(
                            toolShortNames[node?.data?.step?.tool_name] ||
                              tools[node?.data?.step?.tool_name]["tool_name"] ||
                              node?.data?.step?.tool_name,
                            15
                          )}
                        </p>
                      )}
                    />
                  </div>
                </div>
              ) : (
                <></>
              )}
            </div>
          )}
        </ThemeContext.Provider>
      </div>
    </ErrorBoundary>
  );
};
