import { Modal } from "antd";
import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { v4 } from "uuid";
import { AnalysisAgent } from "./AnalysisAgent";
import { AnalysisHistoryItem } from "./AnalysisHistoryItem";
import { AnalysisVersionViewerLinks } from "./AnalysisVersionViewerLinks";
import {
  ArrowRightEndOnRectangleIcon,
  ArrowsPointingOutIcon,
  ArrowsRightLeftIcon,
  PlusIcon,
} from "@heroicons/react/20/solid";
import Papa from "papaparse";
import { sentenceCase, useGhostImage } from "$utils/utils";
import { twMerge } from "tailwind-merge";
import {
  Sidebar,
  Table,
  Toggle,
  TextArea,
  MessageManagerContext,
} from "$ui-components";

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
  predefinedQuestions = [
    "show me 5 rows and create a heatmap",
    "what is the average of x column",
  ],
}) {
  const [activeAnalysisId, setActiveAnalysisId] = useState(null);

  const messageManager = useContext(MessageManagerContext);

  const [activeRootAnalysisId, setActiveRootAnalysisId] = useState(null); // this is the currently selected root analysis

  // we render these in the history panel and don't unmount them
  // for faster switching between them
  const [last10Analysis, setLast10Analysis] = useState([]); // this is the last 10 analysis

  const [sqlOnly, setSqlOnly] = useState(false);

  const ghostImage = useGhostImage();

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
  const analysisDomRefs = useRef({});

  const [loading, setLoading] = useState(false);
  const searchCtr = useRef(null);
  const searchRef = useRef(null);
  const [addToDashboardSelection, setAddToDashboardSelection] = useState(false);
  const [selectedDashboards, setSelectedDashboards] = useState([]);
  const [tableData, setTableData] = useState([]);
  const [tableColumns, setTableColumns] = useState([]);
  const [didUploadFile, setDidUploadFile] = useState(false);

  const [sidebarOpen, setSidebarOpen] = useState(false);

  const uploadFileToServer = async (parsedData) => {
    // upload the file to the server
    setLoading(true);
    console.log(parsedData);
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/integration/upload_csv`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          data: parsedData,
          keyName: keyName,
          token: token,
        }),
      }
    );
    const data = await response.json();
    console.log(data);
    setDidUploadFile(true);
    setLoading(false);
  };

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
            versionList: [newAnalysis],
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

        searchRef.current.value = "";

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

  useEffect(() => {
    function setSearchBar() {
      if (!searchCtr.current) return;

      searchCtr.current.style.left = "0";
      searchCtr.current.style.right = "0";
      searchCtr.current.style.bottom =
        window.innerHeight > 800 ? "30%" : "20px";
    }

    setSearchBar();

    window.addEventListener("resize", setSearchBar);

    return () => {
      window.removeEventListener("resize", setSearchBar);
    };
  }, []);

  // w-0
  return (
    <>
      <div className="relative h-full">
        <div
          className="max-w-full h-full flex flex-row bg-white text-gray-600 w-full"
          id="analysis-version-viewer"
        >
          <div className="absolute h-full left-0 top-2 z-[10] md:sticky md:h-screen">
            <Sidebar
              location="left"
              open={sidebarOpen}
              onChange={(open) => {
                setSidebarOpen(open);
              }}
              title={<span className="font-bold">History</span>}
              rootClassNames={
                "transition-all z-20 h-[calc(100%-1rem)] rounded-md lg:rounded-none lg:rounded-tr-md lg:rounded-br-md bg-gray-100 border h-screen md:h-full sticky top-0 md:relative"
              }
              iconClassNames={`${sidebarOpen ? "" : "text-white bg-primary-highlight"}`}
              openClassNames={"border-gray-300 shadow-md"}
              closedClassNames={"border-transparent bg-transparent shadow-none"}
              contentClassNames={
                // need to add pl-4 here to make the links visible
                "w-72 px-2 pt-5 pb-14 rounded-tl-lg relative sm:block pl-4 min-h-96 h-full overflow-y-auto"
              }
            >
              <div className="flex flex-col text-sm relative history-list">
                <AnalysisVersionViewerLinks
                  analyses={allAnalyses}
                  activeAnalysisId={activeAnalysisId}
                />
                {Object.keys(sessionAnalyses).map((rootAnalysisId, i) => {
                  const root = sessionAnalyses[rootAnalysisId].root;
                  const analysisVersionList =
                    sessionAnalyses[rootAnalysisId].versionList;

                  return (
                    <div key={root.analysisId} className="">
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
                            onClick={() => {
                              if (analysisDomRefs[version.analysisId].ctr) {
                                analysisDomRefs[
                                  version.analysisId
                                ].ctr.scrollIntoView({
                                  behavior: "smooth",
                                  block: "start",
                                  inline: "nearest",
                                });
                              }
                            }}
                            extraClasses={
                              version.isRoot ? "" : "ml-2 border-l-2"
                            }
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
                      className={twMerge(
                        "flex items-center cursor-pointer z-20 relative",
                        "data-[enabled=true]:bg-blue-200 data-[enabled=true]:hover:bg-blue-500 data-[enabled=true]:hover:text-white p-2 data-[enabled=true]:text-blue-400 data-[enabled=true]:shadow-custom ",
                        "data-[enabled=false]:bg-gray-100 data-[enabled=false]:hover:bg-gray-100 data-[enabled=false]:hover:text-gray-400 data-[enabled=false]:text-gray-400 data-[enabled=false]:cursor-not-allowed"
                      )}
                      onClick={() => {
                        if (loading) return;
                        // start a new root analysis
                        setActiveRootAnalysisId(null);
                        setActiveAnalysisId(null);
                      }}
                    >
                      New <PlusIcon className="ml-2 w-4 h-4 inline" />
                    </div>
                    <div className="absolute w-full h-10 bg-gray-100 z-0"></div>
                  </div>
                )}
              </div>
            </Sidebar>
          </div>
          <div
            className="grid grid-cols-1 md:grid-cols-1 grow rounded-tr-lg pb-14 p-2 md:p-4 relative min-w-0 h-full overflow-scroll "
            // onClick={() => {
            //   setSidebarOpen(false);
            // }}
          >
            <div
              className={twMerge(
                "absolute left-0 top-0 h-full w-full overlay md:hidden bg-gray-800 z-[1] transition-all",
                sidebarOpen
                  ? "opacity-30 block"
                  : "opacity-0 pointer-events-none"
              )}
            ></div>
            {activeRootAnalysisId &&
              sessionAnalyses[activeRootAnalysisId].versionList.map(
                (analysis) => {
                  return (
                    <div key={analysis.analysisId}>
                      <AnalysisAgent
                        rootClassNames={
                          "mb-4 ml-3 min-h-96 [&_.analysis-content]:min-h-96 shadow-md analysis-" +
                          analysis.analysisId
                        }
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
                        didUploadFile={didUploadFile}
                        sqlOnly={sqlOnly}
                        onManagerCreated={(mgr, id, ctr) => {
                          analysisDomRefs[id] = {
                            ctr,
                            mgr,
                            id,
                          };
                          // scroll to ctr
                          setTimeout(() => {
                            analysisDomRefs[id].ctr.scrollIntoView({
                              behavior: "smooth",
                              block: "start",
                              inline: "nearest",
                            });
                          }, 100);
                        }}
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
                }
              )}

            {!activeAnalysisId && (
              <div className="grow flex flex-col place-content-center w-full m-auto relative z-[1]">
                {didUploadFile !== true ? (
                  <div className="text-center">
                    <p className="text-gray-400 cursor-default font-bold">
                      Quickstart
                    </p>

                    <ul className="text-gray-400">
                      {predefinedQuestions.map((question, i) => (
                        <li className="" key={i}>
                          <span
                            className="cursor-pointer hover:underline"
                            onClick={(ev) => {
                              ev.preventDefault();

                              handleSubmit(
                                sentenceCase(question),
                                activeRootAnalysisId,
                                !activeRootAnalysisId,
                                activeAnalysisId
                              );
                            }}
                          >
                            {sentenceCase(question)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                <div className="mt-5 m-auto">
                  <label
                    className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
                    htmlFor="file_input"
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
                      let parsedData = null;
                      Papa.parse(file, {
                        dynamicTyping: true,
                        skipEmptyLines: true,
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

                          uploadFileToServer(parsedData);
                        },
                      });
                    }}
                  />
                  {didUploadFile === true ? (
                    <Table rows={tableData} columns={tableColumns} />
                  ) : null}
                </div>
              </div>
            )}

            <div
              className="w-10/12 m-auto lg:w-2/4 fixed z-10 bg-white rounded-lg shadow-custom border border-gray-400 hover:border-blue-500 focus:border-blue-500 flex flex-row"
              style={{
                left: "0",
                right: "0",
                bottom: window.innerHeight > 800 ? "30%" : "20px",
              }}
              ref={searchCtr}
            >
              <div
                className="cursor-move min-h-full w-3 flex items-center ml-1 group"
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setDragImage(ghostImage, 0, 0);
                }}
                onDrag={(e) => {
                  if (!e.clientX || !e.clientY || !searchCtr.current) return;

                  const eBottom =
                    window.innerHeight -
                    e.clientY -
                    searchCtr.current.clientHeight;
                  const eLeft = e.clientX;

                  const minBottom = 20;

                  const maxBottom =
                    window.innerHeight - 20 - searchCtr.current.clientHeight;

                  if (eBottom < minBottom) {
                    searchCtr.current.style.bottom = minBottom + "px";
                  } else if (eBottom > maxBottom) {
                    searchCtr.current.style.bottom = maxBottom + "px";
                  } else {
                    searchCtr.current.style.bottom = eBottom + "px";
                  }

                  const maxLeft =
                    window.innerWidth - searchCtr.current.clientWidth - 20;

                  const minLeft = 20;

                  searchCtr.current.style.right = "auto";

                  if (eLeft < minLeft) {
                    searchCtr.current.style.left = minLeft + "px";
                  } else if (eLeft > maxLeft) {
                    searchCtr.current.style.left = maxLeft + "px";
                  } else {
                    searchCtr.current.style.left = eLeft + "px";
                  }
                }}
              >
                <ArrowsPointingOutIcon className="h-3 w-3 text-gray-400 group-hover:text-primary-text" />
              </div>
              <div className="grow rounded-md md:items-center flex flex-col-reverse md:flex-row">
                <div className="flex flex-row grow">
                  <div className="flex md:flex-row-reverse md:items-center flex-col grow">
                    <TextArea
                      rootClassNames="grow border-none bg-transparent py-1.5 text-gray-900 px-2 placeholder:text-gray-400 sm:leading-6 text-sm break-all focus:ring-0 focus:outline-none"
                      textAreaClassNames="resize-none"
                      ref={searchRef}
                      disabled={loading}
                      defaultRows={1}
                      onKeyDown={(ev) => {
                        if (ev.key === "Enter") {
                          ev.preventDefault();
                          ev.stopPropagation();

                          // if (!searchRef.current.value) return;

                          handleSubmit(
                            searchRef.current.value,
                            activeRootAnalysisId,
                            !activeRootAnalysisId,
                            activeAnalysisId
                          );
                        }
                      }}
                      placeholder={
                        activeRootAnalysisId
                          ? "Type your next question here"
                          : "Type your question here"
                      }
                    />
                    <Toggle
                      disabled={loading}
                      titleClassNames="font-bold text-gray-400"
                      onToggle={(v) => setSqlOnly(v)}
                      defaultOn={sqlOnly}
                      offLabel="SQL/Agents"
                      onLabel={"SQL only"}
                      rootClassNames="items-start md:border-r py-2 md:py-0 px-2 w-36"
                    />
                  </div>
                  <button
                    type="button"
                    className="relative -ml-px inline-flex items-center gap-x-1.5 rounded-r-md px-3 p-0 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-blue-500 hover:bg-blue-500 hover:text-white"
                    onClick={() => {
                      handleSubmit(
                        searchRef.current.value,
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
            </div>
          </div>
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
