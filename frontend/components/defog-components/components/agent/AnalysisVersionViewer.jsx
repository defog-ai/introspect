import { Modal } from "antd";
import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { v4 } from "uuid";
import { AnalysisAgent } from "./AnalysisAgent";
import { PlusOutlined } from "@ant-design/icons";
import { AnalysisHistoryItem } from "./AnalysisHistoryItem";
import { AnalysisVersionViewerLinks } from "./AnalysisVersionViewerLinks";
import { ArrowRightEndOnRectangleIcon } from "@heroicons/react/20/solid";
import Sidebar from "$components/tailwind/Sidebar";
import { MessageManagerContext } from "$components/tailwind/Message";
import Papa from "papaparse";
import { sentenceCase } from "$utils/utils";
import Table from "$components/tailwind/Table";

function AnalysisVersionViewer({
  dashboards,
  token,
  devMode,
  keyName,
  // this isn't always reinforced
  // we check for this only when we're creating a new analysis
  // but not otherwise
  // the priority is to have the new analysis rendered to not lose the manager
  maxRenderedAnalysis = 2,
  // array of strings
  // each string is a question
  predefinedQuestions = ["show me 5 rows", "what is the average of x column"],
}) {
  const [activeAnalysisId, setActiveAnalysisId] = useState(null);

  const messageManager = useContext(MessageManagerContext);

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
  const [tableData, setTableData] = useState([]);
  const [tableColumns, setTableColumns] = useState([]);

  // useEffect(() => {
  //   if (!searchRef.current) return;
  //   const placeholderQuestions = [
  //     "A boxplot of ...",
  //     "Show me the average of ...",
  //     "What is the highest ...",
  //   ];

  //   let idx = 0;
  //   let interval = null;
  //   let timeout = null;
  //   const showNextQuestion = () => {
  //     // show one character at a time
  //     let c = 0;
  //     interval = setInterval(() => {
  //       if (!searchRef.current) return;
  //       searchRef.current.placeholder = placeholderQuestions[idx].slice(0, c);
  //       c++;
  //       if (c > placeholderQuestions[idx].length) {
  //         clearInterval(interval);
  //         idx = (idx + 1) % placeholderQuestions.length;
  //         timeout = setTimeout(showNextQuestion, 2000);
  //       }
  //     }, 80);
  //   };

  //   showNextQuestion();

  //   return () => {
  //     clearInterval(interval);
  //     clearTimeout(timeout);
  //   };
  // });

  const handleSubmit = useCallback(
    (question, rootAnalysisId, isRoot, directParentId) => {
      try {
        setLoading(true);

        // if we have an active root analysis, we're appending to that
        // otherwise we're starting a new analysis
        const newId = "analysis-" + v4();
        let newAnalysis = {
          analysisId: newId,
          isRoot: isRoot,
          rootAnalysisId: isRoot ? newId : rootAnalysisId,
          user_question: question,
        };

        newAnalysis.directParentId = directParentId;

        // this is extra stuff we will send to the backend when creating an entry
        // in the db
        let createAnalysisRequestExtraParams = {
          user_question: question,
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

        console.groupCollapsed("Analysis version viewer");
        console.groupEnd();

        setSessionAnalyses(newSessionAnalyses);
        setActiveAnalysisId(newAnalysis.analysisId);
        setActiveRootAnalysisId(newAnalysis.rootAnalysisId);

        searchRef.current.innerText = "";

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
        messageManager.error("Failed to create analysis");
        console.log(e.stack);
      } finally {
        setLoading(false);
      }
    },
    [sessionAnalyses, allAnalyses]
  );

  // w-0
  return (
    <>
      <div className="relative">
        <div
          className="max-w-full flex flex-col-reverse lg:flex-row bg-gray-50 min-h-96 rounded-md text-gray-600 border border-gray-300 w-full"
          id="analysis-version-viewer"
        >
          <div className="grow rounded-tr-lg pb-14 pt-5 pl-5 relative min-w-0">
            {activeAnalysisId &&
              !last10Analysis.some(
                (analysis) => analysis.analysisId === activeAnalysisId
              ) && (
                // make sure we render the active analysis if clicked
                <div
                  key={activeAnalysisId}
                  className={"relative z-2 overflow-auto"}
                >
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
                    keyName={keyName}
                    initiateAutoSubmit={true}
                    searchRef={searchRef}
                    setGlobalLoading={setLoading}
                    devMode={devMode}
                    onManagerDestroyed={(mgr, id) => {
                      console.log(mgr, id);
                    }}
                  />
                </div>
              )}
            {last10Analysis.map((analysis) => {
              return (
                <div
                  key={analysis.analysisId}
                  className={
                    activeAnalysisId === analysis.analysisId
                      ? "relative z-2 w-full overflow-auto"
                      : "absolute opacity-0"
                  }
                >
                  <AnalysisAgent
                    analysisId={analysis.analysisId}
                    createAnalysisRequestBody={
                      analysis.createAnalysisRequestBody
                    }
                    token={token}
                    keyName={keyName}
                    initiateAutoSubmit={true}
                    searchRef={searchRef}
                    setGlobalLoading={setLoading}
                    devMode={devMode}
                    onManagerDestroyed={(mgr, id) => {
                      const data = mgr.analysisData;
                      // remove the analysis from the sessionAnalyses
                      setSessionAnalyses((prev) => {
                        let newSessionAnalyses = { ...prev };
                        if (newSessionAnalyses[id]) {
                          delete newSessionAnalyses[id];
                        } else {
                          const rootAnalysisId = data.root_analysis_id;
                          if (rootAnalysisId) {
                            const rootAnalysis =
                              newSessionAnalyses[rootAnalysisId];
                            if (rootAnalysis) {
                              rootAnalysis.versionList =
                                rootAnalysis.versionList.filter(
                                  (item) => item.analysisId !== id
                                );
                            }
                          }
                        }

                        return newSessionAnalyses;
                      });
                      setAllAnalyses((prev) => {
                        let newAllAnalyses = { ...prev };
                        if (newAllAnalyses[id]) {
                          delete newAllAnalyses[id];
                        }
                        return newAllAnalyses;
                      });
                      setActiveAnalysisId(null);
                      if (activeRootAnalysisId === id) {
                        setActiveRootAnalysisId(null);
                      }
                    }}
                  />
                </div>
              );
            })}

            {!activeAnalysisId && (
              <div className="h-full flex flex-col place-content-center w-full m-auto relative z-[1]">
                <div className="text-center">
                  <p className="text-gray-400 cursor-default font-bold">
                    Quickstart
                  </p>

                  <ul className="text-gray-400">
                    {predefinedQuestions.map((question, i) => (
                      <li
                        className="cursor-pointer hover:underline"
                        key={i}
                        onClick={(ev) => {
                          ev.preventDefault();
                          ev.stopPropagation();

                          handleSubmit(
                            sentenceCase(question),
                            activeRootAnalysisId,
                            !activeRootAnalysisId,
                            activeAnalysisId
                          );
                        }}
                      >
                        <span className="">{sentenceCase(question)}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mt-5 m-auto">
                  <label
                    className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                    for="file_input"
                  >
                    Upload file
                  </label>
                  <input
                    className="block w-52 text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400"
                    id="file_input"
                    type="file"
                    onChange={(ev) => {
                      const file = ev.target.files[0];
                      if (!file) return;

                      // read file as CSV
                      const config = {
                        dynamicTyping: true,
                        skipEmptyLines: true,
                      };
                      let parsedData = null;
                      Papa.parse(file, {
                        config: config,
                        complete: (results) => {
                          parsedData = results.data;
                          let columns = parsedData[0];
                          // convert headers from a list of strings to a list of objects, where each object has a title and a dataIndex
                          columns = columns.map((title, i) => ({
                            title: title,
                            dataIndex: i,
                            key: title,
                          }));
                          let data = parsedData.slice(1);
                          data = data.map((row, i) => ({
                            key: i,
                            ...Object.fromEntries(
                              columns.map((col, j) => [col.dataIndex, row[j]])
                            ),
                          }));
                          setTableColumns(columns);
                          setTableData(data);
                        },
                      });
                    }}
                  />
                  <Table rows={tableData} columns={tableColumns} />
                </div>
              </div>
            )}

            <div className="w-10/12 m-auto lg:w-3/4 sticky bottom-14 z-10 bg-white right-0 border-2 border-gray-400 p-2 rounded-lg shadow-custom hover:border-blue-500 focus:border-blue-500 flex">
              <div
                className="w-full rounded-none rounded-l-md border py-1.5 text-gray-900 p-1 px-2 placeholder:text-gray-400 sm:leading-6 text-sm break-all focus:ring-0 focus:outline-none"
                ref={searchRef}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter") {
                    ev.preventDefault();
                    ev.stopPropagation();

                    if (!searchRef.current.innerText) return;

                    handleSubmit(
                      searchRef.current.innerText,
                      activeRootAnalysisId,
                      !activeRootAnalysisId,
                      activeAnalysisId
                    );
                  }
                }}
                contentEditable="plaintext-only"
                // placeholder="Show me 5 rows"
                // disabled={loading}
              />
              <button
                type="button"
                className="relative -ml-px inline-flex items-center gap-x-1.5 rounded-r-md px-3 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-blue-500 hover:bg-blue-500 hover:text-white"
                onClick={() => {
                  handleSubmit(
                    searchRef.current.innerText,
                    activeRootAnalysisId,
                    !activeRootAnalysisId,
                    activeAnalysisId
                  );
                }}
              >
                <ArrowRightEndOnRectangleIcon
                  className="-ml-0.5 h-5 w-5 text-gray-400"
                  aria-hidden="true"
                />
                Ask
              </button>
            </div>
          </div>

          {
            <div className="flex flex-col mr-0">
              <Sidebar
                title="History"
                rootClassNames="z-20 rounded-md lg:rounded-none lg:rounded-tr-md bg-gray-100"
                contentClassNames={
                  // need to add pl-4 here to make the links visible
                  "px-2 pt-5 pb-14 rounded-tl-lg relative sm:block pl-4"
                }
              >
                <div className="flex flex-col  relative history-list">
                  <AnalysisVersionViewerLinks
                    analyses={allAnalyses}
                    activeAnalysisId={activeAnalysisId}
                  />
                  {Object.keys(sessionAnalyses).map((rootAnalysisId, i) => {
                    const root = sessionAnalyses[rootAnalysisId].root;
                    const analysisVersionList =
                      sessionAnalyses[rootAnalysisId].versionList;

                    return (
                      <div key={root.analysisId}>
                        <AnalysisHistoryItem
                          analysis={root}
                          isActive={activeAnalysisId === root.analysisId}
                          setActiveRootAnalysisId={setActiveRootAnalysisId}
                          setActiveAnalysisId={setActiveAnalysisId}
                          setAddToDashboardSelection={
                            setAddToDashboardSelection
                          }
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
                      </div>
                    );
                  })}
                  {!activeRootAnalysisId ? (
                    <AnalysisHistoryItem
                      isDummy={true}
                      setActiveRootAnalysisId={setActiveRootAnalysisId}
                      setActiveAnalysisId={setActiveAnalysisId}
                      isActive={!activeRootAnalysisId}
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
              </Sidebar>
            </div>
          }
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
