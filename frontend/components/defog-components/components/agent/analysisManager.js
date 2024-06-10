import { createAnalysis, getAnalysis, getToolRunData } from "$utils/utils";

// the name of the prop where the data is stored for each stage
const propNames = {
  clarify: "clarification_questions",
  gen_approaches: "approaches",
  gen_steps: "steps",
  gen_report: "report_sections",
};

const agentRequestTypes = ["clarify", "gen_steps"];

function AnalysisManager({
  analysisId,
  mainSocket,
  rerunSocket,
  onNewData = () => {},
  onReRunData = () => {},
  token,
  devMode,
  createAnalysisRequestBody = {},
}) {
  let analysisData = null;
  let toolRunDataCache = {};
  let reRunningSteps = [];
  let wasNewAnalysisCreated = false;
  let listeners = [];

  function getAnalysisData() {
    return analysisData;
  }

  function setAnalysisData(newVal) {
    analysisData = newVal;
    analysisData["currentStage"] = getCurrentStage();
    analysisData["nextStage"] = getNextStage();
    emitDataChange();
  }

  async function init() {
    if (analysisData) return;

    let retries = 0;

    console.log("Analysis Manager init");
    // get report data
    let fetchedAnalysisData = null;
    let newAnalysisCreated = false;
    const res = await getAnalysis(analysisId);
    if (!res.success) {
      // create a new analysis
      fetchedAnalysisData = await createAnalysis(
        token,
        analysisId,
        createAnalysisRequestBody
      );

      if (!fetchedAnalysisData.success || !fetchedAnalysisData.report_data) {
        // this is a hacky fix for collaboration on documents.
        // this might be an analysis that has been create already
        // when a user creates an analysis on one doc, the yjs updates before
        // the analysis can be added to the db. so another person on the same doc will get an error if
        // they try to query the db too quickly.
        // So we retry a few times
        // retry after 1 second
        if (retries < 2) {
          retries++;
          console.log("Analysis Manager retrying");
          await new Promise((resolve) => setTimeout(resolve, 1000)).then(
            async () => {
              await init();
            }
          );
        }

        // if more than 2 retries
        // stop loading, throw error
        throw new Error(fetchedAnalysisData?.error_message);
      } else {
        fetchedAnalysisData = fetchedAnalysisData.report_data;
      }

      newAnalysisCreated = true;
    } else {
      fetchedAnalysisData = res.report_data;
    }

    wasNewAnalysisCreated = newAnalysisCreated;
    // update the analysis data
    setAnalysisData(fetchedAnalysisData);
  }

  function getCurrentStage() {
    const lastExistingStage = Object.keys(analysisData)
      .filter((d) => agentRequestTypes.includes(d))
      .sort(
        (a, b) => agentRequestTypes.indexOf(a) - agentRequestTypes.indexOf(b)
      )
      .pop();

    return lastExistingStage;
  }

  function getNextStage() {
    const currentStage = getCurrentStage();
    const nextStageIndex = agentRequestTypes.indexOf(currentStage) + 1;

    return agentRequestTypes[nextStageIndex];
  }

  function submit(query, stageInput = {}, submitSourceStage = null) {
    if (!mainSocket || !mainSocket?.isConnected()) {
      throw new Error("Not connected to servers. Trying to reconnect.");
    }

    const nextStage = getNextStage();
    const prop = propNames[nextStage];

    const body = {
      ...stageInput,
      request_type: nextStage,
      report_id: analysisId,
      user_question: query,
      skip_intro: true,
      skip_conclusion: true,
      max_approaches: 1,
      skip_extra_approaches: true,
      skip_text_gen: true,
      token: token,
      db_creds: null,
      dev: devMode,
    };

    console.groupCollapsed("Analysis Manager submitting");
    console.log("Submitting", analysisData);
    console.groupEnd();

    mainSocket.send(body);

    const newAnalysisData = { ...analysisData };
    newAnalysisData["user_question"] = query;
    // create empty array if doesn't exist
    if (!newAnalysisData?.[nextStage]) {
      newAnalysisData[nextStage] = { success: true, [prop]: [] };
    }

    setAnalysisData(newAnalysisData);
  }

  function setMainSocket(newSocket) {
    mainSocket = newSocket;
  }

  function setReRunSocket(newSocket) {
    rerunSocket = newSocket;
  }

  function onMainSocketMessage(event) {
    let response;
    let newAnalysisData = null;
    try {
      if (!event.data) {
        throw new Error(
          "Something went wrong. Please try again or contact us if this persists."
        );
      }

      response = JSON.parse(event.data);

      // if the response's analysis_id isn't this analysisId, ignore
      if (response?.analysis_id !== analysisId) return;

      if (response?.error_message) {
        throw new Error(response.error_message);
      }

      const rType = response.request_type;
      const prop = propNames[rType];

      const nextStage = agentRequestTypes[agentRequestTypes.indexOf(rType) + 1];

      newAnalysisData = { ...analysisData };

      if (nextStage) {
        // if any of the stages including and after nextStage exists
        // remove all data from those stages (to mimic what happens on the backend)
        let idx = agentRequestTypes.indexOf(nextStage) + 1;
        if (idx < agentRequestTypes.length) {
          while (idx < agentRequestTypes.length) {
            delete newAnalysisData[agentRequestTypes[idx]];
            idx++;
          }
        }
      }

      if (response.output && response.output.success && response.output[prop]) {
        if (!newAnalysisData[rType]) {
          newAnalysisData = { ...newAnalysisData, [rType]: response.output };
        } else {
          // check if the response has an "overwrite_key"
          // if there's an overwrite_key provided,
          // then go through old data, and the new_data
          // if the overwrite_key is found in the old data, replace it with the elements that exist new_data with the same overwrite_key
          // if it's not found, just append the item to the end
          const overwrite_key = response.overwrite_key;
          if (overwrite_key) {
            const newToolRunDataCache = { ...toolRunDataCache };
            response.output[prop].forEach(async (res) => {
              const idx = newAnalysisData[rType][prop].findIndex(
                (d) => d[overwrite_key] === res[overwrite_key]
              );

              if (idx > -1) {
                newAnalysisData[rType][prop][idx] = res;
                if (rType === "gen_steps" && res.tool_run_id) {
                  // if this is gen_steps, we also need to update the latest tool run data
                  // update it in the cache
                  const updatedData = await getToolRunData(res.tool_run_id);
                  if (updatedData.success) {
                    newToolRunDataCache[updatedData.tool_run_id] = updatedData;
                  }
                }
              } else {
                newAnalysisData[rType][prop].push(res);
              }
            });
            toolRunDataCache = newToolRunDataCache;
          } else {
            newAnalysisData[rType][prop] = newAnalysisData[rType][prop].concat(
              response.output[prop]
            );
          }
        }
      }

      setAnalysisData(newAnalysisData);
    } catch (e) {
      console.log(e);
      response = { error_message: e };
      newAnalysisData = null;
    } finally {
      if (onNewData && typeof onNewData === "function") {
        onNewData(response, newAnalysisData);
      }
    }
  }

  function initiateReRun(toolRunId, preRunActions) {
    if (!rerunSocket.isConnected()) {
      throw new Error("Not connected to servers. Trying to reconnect.");
    }

    const newAnalysisData = { ...analysisData };

    if (
      preRunActions &&
      preRunActions?.action === "add_step" &&
      preRunActions?.new_step
    ) {
      // add the new step to analysisData
      newAnalysisData.gen_steps.steps.push(preRunActions.new_step);
      // update the analysis data
      analysisData = newAnalysisData;
    }

    if (rerunSocket && rerunSocket.send) {
      rerunSocket.send({
        tool_run_id: toolRunId,
        analysis_id: analysisId,
        dev: devMode,
      });
    }
  }

  async function onReRunSocketMessage(event) {
    const response = JSON.parse(event.data);

    if (response?.analysis_id !== analysisId) return;

    console.groupCollapsed("Analysis manager re run");
    console.log(response);

    let newReRunningSteps = reRunningSteps.slice();

    // re run messages can be of two types:
    // 1. which step is GOING TO BE RUN. this won't just be the step that was asked to be re run by the user.
    // this can also be the step's parents and it's children.
    // 2. the result of a re run of a step
    if (response.pre_tool_run_message) {
      // means this is just a notification that this step is going to be re run
      // so add this step to rerunning steps
      // this has better UX: lets us move and click around the dag on
      // any node but the currently rerunning step
      console.log("step re running started: ", response.pre_tool_run_message);

      newReRunningSteps.push({
        tool_run_id: response.pre_tool_run_message,
      });
    } else {
      if (!response.success) {
        throw new Error(response?.error_message);
      }
      // remove the tool run id from rerunning steps and clear it's timeout
      newReRunningSteps = newReRunningSteps.filter((d) => {
        return d.tool_run_id !== response.tool_run_id;
      });
    }

    let newToolRunDataCache = { ...toolRunDataCache };
    if (response.success) {
      newToolRunDataCache[response.tool_run_id] = Object.assign({}, response);
    }

    // if this re run has an error_message (or if it doesn't), update the analysisSteps
    const newAnalysisData = { ...analysisData };

    const newSteps = newAnalysisData.gen_steps.steps.slice();

    const idx = newSteps.findIndex(
      (d) => d.tool_run_id === response.tool_run_id
    );
    if (idx > -1) {
      newSteps[idx] = {
        ...newSteps[idx],
        error_message: response?.tool_run_data?.error_message,
      };
    }

    newAnalysisData.gen_steps.steps = newSteps;

    reRunningSteps = newReRunningSteps;
    toolRunDataCache = newToolRunDataCache;

    setAnalysisData(newAnalysisData);
    console.groupEnd();

    if (onReRunData && typeof onReRunData === "function") {
      onReRunData(response);
    }
  }

  let mainListenerIdx = null;
  let rerunListenerIdx = null;

  function addEventListeners() {
    mainListenerIdx = mainSocket.addEventListener(
      "message",
      onMainSocketMessage
    );
    rerunListenerIdx = rerunSocket.addEventListener(
      "message",
      onReRunSocketMessage
    );
  }

  function removeEventListeners() {
    mainSocket.removeEventListener(
      "message",
      onMainSocketMessage,
      mainListenerIdx
    );
    rerunSocket.removeEventListener(
      "message",
      onReRunSocketMessage,
      rerunListenerIdx
    );
  }

  function subscribeToDataChanges(listener) {
    listeners = [...listeners, listener];

    return function unsubscribe() {
      listeners = listeners.filter((l) => l !== listener);
    };
  }

  function emitDataChange() {
    listeners.forEach((l) => l());
  }

  return {
    init,
    get wasNewAnalysisCreated() {
      return wasNewAnalysisCreated;
    },
    set wasNewAnalysisCreated(val) {
      wasNewAnalysisCreated = val;
    },
    get analysisData() {
      return Object.assign({}, analysisData);
    },
    set analysisData(val) {
      analysisData = val;
    },
    get toolRunDataCache() {
      return Object.assign({}, toolRunDataCache);
    },
    set toolRunDataCache(val) {
      toolRunDataCache = val;
    },
    get reRunningSteps() {
      return reRunningSteps.slice();
    },
    set reRunningSteps(val) {
      reRunningSteps = val;
    },
    getAnalysisData,
    subscribeToDataChanges,
    addEventListeners,
    removeEventListeners,
    submit,
    initiateReRun,
    setMainSocket,
    setReRunSocket,
  };
}

export default AnalysisManager;
