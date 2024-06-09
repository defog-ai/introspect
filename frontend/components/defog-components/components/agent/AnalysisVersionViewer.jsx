import { Input, Modal, message } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";
import { v4 } from "uuid";
import { AnalysisAgent } from "./AnalysisAgent";
import { PlusOutlined, StarOutlined } from "@ant-design/icons";
import { appendAnalysisToYjsDoc } from "$utils/utils";
import setupBaseUrl from "$utils/setupBaseUrl";
import { Doc, applyUpdate, encodeStateAsUpdate } from "yjs";
import YPartyKitProvider from "y-partykit/provider";
import { AnalysisHistoryItem } from "./AnalysisHistoryItem";
import { AnalysisVersionViewerLinks } from "./AnalysisVersionViewerLinks";

const partyEndpoint = process.env.NEXT_PUBLIC_AGENTS_ENDPOINT;

function AnalysisVersionViewer({
  dashboards,
  token,
  devMode,
  // this isn't always reinforced
  // we check for this only when we're creating a new analysis
  // but not otherwise
  // the priority is to have the new analysis rendered to not lose the manager
  maxRenderedAnalysis = 2,
}) {
  const [activeAnalysisId, setActiveAnalysisId] = useState(null);

  const [activeRootAnalysisId, setActiveRootAnalysisId] = useState(null); // this is the currently selected root analysis

  // we render these in the history panel and don't unmount them
  // for faster switching between them
  const [last10Analysis, setLast10Analysis] = useState([]); // this is the last 10 analysis

  // an object that stores all analysis in this "session"
  // structure:
  // {
  //  rootAnalysisId: {
  //     root: {
  //       analysisId: "analysis-1",
  //       user_question: "Show me 5 rows",
  //     },
  //     versionList: [
  //       {
  //        analysisId: "analysis-1-v1",
  //        user_question: "Show me 5 rows",
  //        manager: ...
  //       },
  //      ...
  //    ]
  //   }
  //  ...
  // }
  const [sessionAnalyses, setSessionAnalyses] = useState({});
  // just a duplicate of the above but in a flat object
  const [allAnalyses, setAllAnalyses] = useState({});

  const [loading, setLoading] = useState(false);
  const searchRef = useRef(null);
  const [addToDashboardSelection, setAddToDashboardSelection] = useState(false);
  const [selectedDashboards, setSelectedDashboards] = useState([]);

  const managerCreatedHook = (manager, analysisId) => {
    // add manager to analysisVersionList
    // let newAnalysisVersionList = analysisVersionList.map((item) => {
    //   if (item.analysisId === analysisId) {
    //     return {
    //       ...item,
    //       manager,
    //     };
    //   }
    //   return item;
    // });
    // setAnalysisVersionList(newAnalysisVersionList);
  };

  useEffect(() => {
    if (!searchRef.current) return;
    const placeholderQuestions = [
      "Show me 5 rows",
      "A boxplot of ...",
      "Show me the average of ...",
      "A chart showing ...",
    ];

    let idx = 0;
    let interval = null;
    let timeout = null;
    const showNextQuestion = () => {
      // show one character at a time
      let c = 0;
      interval = setInterval(() => {
        if (!searchRef.current) return;
        searchRef.current.input.placeholder = placeholderQuestions[idx].slice(
          0,
          c
        );
        c++;
        if (c > placeholderQuestions[idx].length) {
          clearInterval(interval);
          idx = (idx + 1) % placeholderQuestions.length;
          timeout = setTimeout(showNextQuestion, 2000);
        }
      }, 80);
    };

    showNextQuestion();

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  });

  const handleSubmit = useCallback(
    (rootAnalysisId, isRoot, directParentId) => {
      try {
        setLoading(true);

        // if we have an active root analysis, we're appending to that
        // otherwise we're starting a new analysis
        const newId = "analysis-" + v4();
        let newAnalysis = {
          analysisId: newId,
          isRoot: isRoot,
          rootAnalysisId: isRoot ? newId : rootAnalysisId,
          user_question: searchRef.current.input.value,
        };

        newAnalysis.directParentId = directParentId;

        // this is extra stuff we will send to the backend when creating an entry
        // in the db
        let createAnalysisRequestExtraParams = {
          user_question: searchRef.current.input.value,
          is_root_analysis: isRoot,
          root_analysis_id: rootAnalysisId,
          direct_parent_id: directParentId,
        };

        newAnalysis.createAnalysisRequestBody = {
          // the backend receives an extra param called "other_data" when appending to the table
          other_data: createAnalysisRequestExtraParams,
        };

        let newSessionAnalyses = { ...sessionAnalyses };

        // if we have an active root analysis, we're appending to that
        // otherwise we're starting a new root analysis
        if (!rootAnalysisId) {
          setActiveRootAnalysisId(newAnalysis.analysisId);
          newSessionAnalyses[newAnalysis.analysisId] = {
            root: newAnalysis,
            versionList: [],
          };
        } else {
          const rootAnalysis = sessionAnalyses[rootAnalysisId].root;
          newSessionAnalyses[rootAnalysis.analysisId].versionList.push(
            newAnalysis
          );
        }

        // // check if the last analysis is not a dummy analysis
        // // and either:
        // // doesn't have gen_steps as the nextStage
        // // or has gen_steps as the nextStage but the gen_steps is empty
        // // if so, delete this from the list and create a new analysis
        // const lastAnalysis =
        //   newAnalysisVersionList?.[newAnalysisVersionList.length - 1];
        // const lastAnalysisData = lastAnalysis?.manager?.analysisData;

        // if (
        //   lastAnalysis &&
        //   lastAnalysisData &&
        //   lastAnalysis.analysisId !== "dummy" &&
        //   // either no steps or non existent steps
        //   !lastAnalysisData?.gen_steps?.steps?.length
        // ) {
        //   console.log(
        //     "the last analysis was still at clarify stage, deleting it and starting a fresh one"
        //   );
        //   newAnalysisVersionList = newAnalysisVersionList.slice(
        //     0,
        //     newAnalysisVersionList.length - 1
        //   );
        //   directParentIndex = newAnalysisVersionList.length - 1;
        // }

        // let newAnalysisId = null;

        console.groupCollapsed("Analysis version viewer");
        console.groupEnd();

        setSessionAnalyses(newSessionAnalyses);
        setActiveAnalysisId(newAnalysis.analysisId);
        setActiveRootAnalysisId(newAnalysis.rootAnalysisId);
        searchRef.current.input.value = "";
        setAllAnalyses({
          ...allAnalyses,
          [newAnalysis.analysisId]: newAnalysis,
        });
        // remove the earliest one only if we have more than 10
        setLast10Analysis((prev) => {
          if (prev.length >= maxRenderedAnalysis) {
            return [...prev.slice(1), newAnalysis];
          } else {
            return [...prev, newAnalysis];
          }
        });
      } catch (e) {
        message.error("Failed to create analysis: " + e);
      } finally {
        setLoading(false);
      }
    },
    [sessionAnalyses, allAnalyses]
  );

  // w-0
  return (
    <>
      <div
        className="flex flex-col bg-gray-50 min-h-96 rounded-md text-gray-600 border border-gray-300"
        id="analysis-version-viewer"
      >
        <div className="flex grow">
          <div className="basis-3/4 rounded-tr-lg pb-14 pt-5 pl-5 relative">
            {activeAnalysisId &&
              !last10Analysis.some(
                (analysis) => analysis.analysisId === activeAnalysisId
              ) && (
                // make sure we render the active analysis if clicked
                <div key={activeAnalysisId} className={"relative z-2"}>
                  <AnalysisAgent
                    analysisId={activeAnalysisId}
                    createAnalysisRequestBody={
                      // just a little fucked.
                      activeAnalysisId === activeRootAnalysisId
                        ? sessionAnalyses[activeRootAnalysisId].root
                            .createAnalysisRequestBody
                        : sessionAnalyses[
                            activeRootAnalysisId
                          ].versionList.find(
                            (item) => item.analysisId === activeAnalysisId
                          ).createAnalysisRequestBody
                    }
                    token={token}
                    initiateAutoSubmit={true}
                    searchRef={searchRef}
                    setGlobalLoading={setLoading}
                    managerCreatedHook={managerCreatedHook}
                    devMode={devMode}
                  />
                </div>
              )}
            {last10Analysis.map((analysis) => {
              return (
                <div
                  key={analysis.analysisId}
                  className={
                    activeAnalysisId === analysis.analysisId
                      ? "relative z-2"
                      : "absolute opacity-0"
                  }
                >
                  <AnalysisAgent
                    analysisId={analysis.analysisId}
                    createAnalysisRequestBody={
                      analysis.createAnalysisRequestBody
                    }
                    token={token}
                    initiateAutoSubmit={true}
                    searchRef={searchRef}
                    setGlobalLoading={setLoading}
                    managerCreatedHook={managerCreatedHook}
                    devMode={devMode}
                  />
                </div>
              );
            })}
            {!activeAnalysisId && (
              <div className="w-full h-full place-content-center m-auto">
                <p className="w-1/4 m-auto text-gray-400 text-center">
                  Ask and press Enter
                </p>
              </div>
            )}
          </div>

          {
            <div className="flex flex-col basis-1/4 mr-0 px-2 pt-5 pb-14 bg-gray-100 rounded-tl-lg relative">
              <h2 className="px-2 mb-3">History</h2>
              <div className="flex flex-col px-2 relative history-list">
                <AnalysisVersionViewerLinks
                  analyses={allAnalyses}
                  activeAnalysisId={activeAnalysisId}
                />
                {Object.keys(sessionAnalyses).map((rootAnalysisId, i) => {
                  const root = sessionAnalyses[rootAnalysisId].root;
                  const analysisVersionList =
                    sessionAnalyses[rootAnalysisId].versionList;

                  return (
                    <>
                      <AnalysisHistoryItem
                        key={root.analysisId}
                        analysis={root}
                        isActive={activeAnalysisId === root.analysisId}
                        setActiveRootAnalysisId={setActiveRootAnalysisId}
                        setActiveAnalysisId={setActiveAnalysisId}
                        setAddToDashboardSelection={setAddToDashboardSelection}
                        extraClasses={"mt-2"}
                      />
                      {analysisVersionList.map((version, i) => {
                        return (
                          <AnalysisHistoryItem
                            key={version.analysisId}
                            analysis={version}
                            isActive={activeAnalysisId === version.analysisId}
                            setActiveRootAnalysisId={setActiveRootAnalysisId}
                            setActiveAnalysisId={setActiveAnalysisId}
                            setAddToDashboardSelection={
                              setAddToDashboardSelection
                            }
                            extraClasses="ml-2 border-l-2"
                          />
                        );
                      })}
                    </>
                  );
                })}
                {!activeRootAnalysisId ? (
                  <AnalysisHistoryItem
                    isDummy={true}
                    setActiveRootAnalysisId={setActiveRootAnalysisId}
                    setActiveAnalysisId={setActiveAnalysisId}
                    isActive={!activeRootAnalysisId}
                    extraClasses={"mt-2"}
                  />
                ) : (
                  <div className="w-full mt-5 sticky bottom-5">
                    <div
                      data-enabled={!loading}
                      className={
                        "cursor-pointer z-20 relative " +
                        "data-[enabled=true]:bg-blue-200 data-[enabled=true]:hover:bg-blue-500 data-[enabled=true]:hover:text-white p-2 data-[enabled=true]:text-blue-400 data-[enabled=true]:shadow-custom " +
                        "data-[enabled=false]:bg-gray-100 data-[enabled=false]:hover:bg-gray-100 data-[enabled=false]:hover:text-gray-400 data-[enabled=false]:text-gray-400 data-[enabled=false]:cursor-not-allowed"
                      }
                      onClick={() => {
                        if (loading) return;
                        // start a new root analysis
                        setActiveRootAnalysisId(null);
                        setActiveAnalysisId(null);
                      }}
                    >
                      New <PlusOutlined />
                    </div>
                    <div className="absolute w-full h-10 bg-gray-100 z-0"></div>
                  </div>
                )}
              </div>
            </div>
          }
        </div>
        <div className="sticky bottom-14 z-10">
          <Input
            type="text"
            ref={searchRef}
            onPressEnter={(ev) => {
              // whenever we submit, we either start a new analysis or append to the current one
              // based on where the user is currently in the UI
              handleSubmit(
                activeRootAnalysisId,
                !activeRootAnalysisId,
                activeAnalysisId
              );
            }}
            placeholder="Show me 5 rows"
            disabled={loading}
            rootClassName="bg-white absolute mx-auto -left-1/4 right-0 border-2 border-gray-400 -bottom-8 p-2 rounded-lg w-full lg:w-6/12 mx-auto h-16 shadow-custom hover:border-blue-500 focus:border-blue-500"
          />
        </div>
      </div>
      <Modal
        title="Select the dashboards to add this analysis to"
        open={addToDashboardSelection}
        onOk={() => {
          console.log(selectedDashboards);
          return;
        }}
        onCancel={() => {
          setAddToDashboardSelection(false);
        }}
      >
        <div className="dashboard-selection mt-8 flex flex-col max-h-80 overflow-scroll bg-gray-100 rounded-md">
          {dashboards.map((dashboard) => (
            <div
              className={
                "flex flex-row p-2 hover:bg-gray-200 cursor-pointer text-gray-400 items-start " +
                (selectedDashboards.includes(dashboard.doc_id) &&
                  "text-gray-600 font-bold")
              }
              key={dashboard.doc_id}
              onClick={() => {
                if (selectedDashboards.includes(dashboard.doc_id)) {
                  setSelectedDashboards(
                    selectedDashboards.filter(
                      (item) => item !== dashboard.doc_id
                    )
                  );
                } else {
                  setSelectedDashboards([
                    ...selectedDashboards,
                    dashboard.doc_id,
                  ]);
                }
              }}
            >
              <div className="checkbox mr-3">
                <input
                  // style input to have no background and a black tick
                  className="appearance-none w-3 h-3 border border-gray-300 rounded-md checked:bg-blue-600 checked:border-transparent"
                  type="checkbox"
                  checked={selectedDashboards.includes(dashboard.doc_id)}
                  readOnly
                />
              </div>
              <div className="grow">{dashboard.doc_title}</div>
            </div>
          ))}
        </div>
      </Modal>
    </>
  );
}

export default AnalysisVersionViewer;
