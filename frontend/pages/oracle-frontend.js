import { Button, Input, Row, Col, Select, Spin, Checkbox } from "antd";
import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import Sources from "$components/oracle/Sources";
import TaskType from "$components/oracle/TaskType";
import ReportStatus from "$components/oracle/ReportStatus";
import setupBaseUrl from "$utils/setupBaseUrl";
import { useRouter } from "next/router";
import {
  CheckCircleOutlined,
  CloseOutlined,
  DeleteOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  InfoCircleOutlined,
  SendOutlined
} from "@ant-design/icons";
import { Tooltip } from "antd";

const { TextArea } = Input;

function OracleDashboard() {
  const [apiKeyName, setApiKeyName] = useState(null);
  const [apiKeyNames, setApiKeyNames] = useState([]);
  const [isPolling, setIsPolling] = useState(false);
  const router = useRouter();

  const getApiKeyNames = async (token) => {
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_api_key_names",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
        }),
      }
    );
    if (!res.ok) {
      throw new Error(
        "Failed to get api key names - are you sure your network is working?"
      );
    }
    const data = await res.json();
    setApiKeyNames(data.api_key_names);
    setApiKeyName(data.api_key_names[0]);
  };

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    getApiKeyNames(token);
  }, []);

  useEffect(() => {
    if (!apiKeyName) return;
    // check DB / backend API readiness
    checkReady();

    // the effect runs after the apiKeyName fetches / changes as our checks
    // depend on the api key
  }, [apiKeyName]);

  const [ready, setReady] = useState(false);
  const [readyErrorMsg, setReadyErrorMsg] = useState("");
  const [userQuestion, setUserQuestion] = useState("");

  const answers = useRef({});
  const [clarifications, setClarifications] = useState([]);
  const [answerLastUpdateTs, setAnswerLastUpdateTs] = useState(Date.now());
  const [waitClarifications, setWaitClarifications] = useState(false);
  const [taskType, setTaskType] = useState(null);
  const [sources, setSources] = useState([]);
  const [reports, setReports] = useState([]);

  const handleTaskTypeChange = (value) => {
    setTaskType(value);
  };

  const checkReady = useCallback(async () => {
    if (!apiKeyName) return;
    const token = localStorage.getItem("defogToken");
    const resCheck = await fetch(setupBaseUrl("http", `integration/check`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token: token,
        key_name: apiKeyName,
      }),
    });

    if (resCheck.ok) {
      setReady(true);
      setReadyErrorMsg("");
      console.log("Backend ready to generate reports");
    } else {
      const data = await resCheck.json();
      setReady(false);
      setReadyErrorMsg(data.error);
      console.error("Backend not ready to generate reports");
    }
  }, [apiKeyName]);

  // Function that will update the list of clarifications given the clarification
  // and the answer.
  const updateAnsweredClarifications = (clarification, answer) => {
    // if answer is a list (checkboxes), convert it to a comma-delimited string
    if (Array.isArray(answer)) {
      answer = answer.join(", ");
    }

    answers.current[clarification] = answer;

    setAnswerLastUpdateTs(Date.now());
  };

  const getClarifications = async () => {
    if (!userQuestion) return;

    setWaitClarifications(true);
    const token = localStorage.getItem("defogToken");
    if (!ready) {
      console.log("DB not ready yet, re checking...");
      setWaitClarifications(false);
      // check if the DB is ready again
      checkReady();
      return;
    }
    // answeredClarifications would be a list of clarifications that have been answered
    // by the user.
    let answeredClarifications = clarifications
      .filter(
        (clarificationObject) =>
          answers.current[clarificationObject.clarification]
      )
      .map((clarificationObject) => ({
        ...clarificationObject,
        answer: answers.current?.[clarificationObject.clarification],
      }));

    console.log("answered clarifications:", answeredClarifications);

    const res = await fetch(setupBaseUrl("http", `oracle/clarify_question`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token: token,
        key_name: apiKeyName,
        user_question: userQuestion,
        task_type: taskType,
        answered_clarifications: answeredClarifications,
      }),
    });
    setWaitClarifications(false);
    if (res.ok) {
      const data = await res.json();

      // hard-code all task types to exploration
      setTaskType("exploration");
      // get the updated answered clarifications, since the user might have
      // answered some clarifications while the request was processing
      let answeredClarifications = clarifications.filter(
        (clarificationObject) =>
          answers.current[clarificationObject.clarification]
      );

      // concatenate the new clarifications with the answered clarifications
      setClarifications(answeredClarifications.concat(data.clarifications));
    } else {
      console.error("Failed to fetch clarifications");
    }
  };

  const deleteClarification = (index, clarificationObject) => {
    // Allow users to delete any clarification through UI
    setClarifications((prevClarifications) =>
      prevClarifications.filter((_, i) => i !== index)
    );
    // Remove from answers as well
    answers.current[clarificationObject.clarification] = undefined;
  };

  const getSources = async () => {
    const token = localStorage.getItem("defogToken");
    const res = await fetch(
      setupBaseUrl("http", `oracle/suggest_web_sources`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
          user_question: userQuestion,
        }),
      }
    );
    if (res.ok) {
      const data = await res.json();
      // we only use the list of organic search results, discarding the rest for now
      const sourcesNew = data.organic;
      // add a selected field to each source
      sourcesNew.forEach((source) => {
        source.selected = false;
        source.key = source.link;
      });
      setSources(sourcesNew);
    } else {
      console.error("Failed to fetch sources");
    }
  };

  const fetchReports = useCallback(async (apiKeyName, setReportsCallback) => {
    try {
      const token = localStorage.getItem("defogToken");
      if (!token || !apiKeyName) return;

      const res = await fetch(setupBaseUrl("http", `oracle/list_reports`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
          key_name: apiKeyName,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setReportsCallback(data.reports);
        return data.reports;
      } else {
        console.error("Failed to fetch reports");
        return null;
      }
    } catch (error) {
      console.error("An error occurred while fetching reports:", error);
      return null;
    }
  }, []);

  useEffect(() => {
    let intervalId;

    // fetch initial reports
    const fetchInitial = async () => {
      const reports = await fetchReports(apiKeyName, setReports);
      if (reports) {
        const allTerminal = reports.every(
          (report) => report.status === "done" || report.status === "error"
        );
        if (!allTerminal) {
          setIsPolling(true);
        }
      }
    };
    fetchInitial();

    const pollReports = async () => {
      const reports = await fetchReports(apiKeyName, setReports);

      if (reports) {
        // make sure all reports are in a terminal state i.e. done or error
        const allTerminal = reports.every(
          (report) => report.status === "done" || report.status === "error"
        );

        if (allTerminal) {
          setIsPolling(false);
          clearInterval(intervalId);
        }
      } else {
        setIsPolling(false);
        clearInterval(intervalId);
      }
    };

    if (isPolling) {
      intervalId = setInterval(pollReports, 1000); // poll every second
      pollReports(); // poll immediately for the first time
    }

    return () => clearInterval(intervalId);
  }, [isPolling, apiKeyName]);

  const getMDX = useCallback(
    async (reportId) => {
      const token = localStorage.getItem("defogToken");
      const res = await fetch(setupBaseUrl("http", `oracle/get_report_mdx`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/pdf",
          // disable cors for the download
          mode: "no-cors",
        },
        body: JSON.stringify({
          key_name: apiKeyName,
          token: token,
          report_id: reportId,
        }),
      });

      const data = await res.json();

      console.log(data);

      if (!data.mdx) {
        console.log("Could not getch MDX for report:", reportId);
      }
    },
    [apiKeyName]
  );

  const downloadReport = async (report_id) => {
    // Fetch the token from localStorage
    const token = localStorage.getItem("defogToken");
    console.log("Downloading report", report_id);

    try {
      // Make the API request
      const res = await fetch(setupBaseUrl("http", `oracle/download_report`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/pdf",
          // disable cors for the download
          mode: "no-cors",
        },
        body: JSON.stringify({
          token,
          key_name: apiKeyName, // Make sure apiKeyName is defined in your scope
          report_id: report_id,
        }),
      });

      // Check if the request was successful
      if (res.ok) {
        console.log("Download successful");

        // Create a blob from the response
        const blob = await res.blob();

        // Create a URL for the blob
        const url = window.URL.createObjectURL(blob);

        // Create a temporary anchor element to trigger the download
        const a = document.createElement("a");
        a.href = url;
        a.download = `report_${report_id}.pdf`; // Specify the filename
        document.body.appendChild(a);
        a.click();

        // Clean up by revoking the object URL and removing the anchor element
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        console.error("Download failed with status", res.status);
      }
    } catch (error) {
      // send a toast of the error message
      console.error(error.message);
    }
  };

  const deleteReport = async (report_id) => {
    // Fetch the token from localStorage
    const token = localStorage.getItem("defogToken");

    try {
      // Send delete request to the API
      const res = await fetch(setupBaseUrl("http", `oracle/delete_report`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
          key_name: apiKeyName,
          report_id: report_id,
        }),
      });

      if (res.ok) {
        // Re-fetch reports after successful deletion
        console.log("Report deleted successfully");
        await fetchReports(apiKeyName, setReports);
      } else {
        console.error("Failed to delete report");
      }
    } catch (error) {
      console.error("Error deleting report:", error);
    }
  };

  const generateReport = async () => {
    // Logic for generating a report
    const token = localStorage.getItem("defogToken");
    const selectedSourceLinks = sources
      .filter((source) => source.selected)
      .map((source) => source.link);

    const res = await fetch(setupBaseUrl("http", `oracle/begin_generation`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token,
        key_name: apiKeyName,
        user_question: userQuestion,
        sources: selectedSourceLinks,
        task_type: taskType,
        clarifications: [
          ...clarifications.map((d) => ({
            ...d,
            answer: answers.current[d.clarification],
          })),
          // Add additional comments as a special clarification if present
          ...(answers.current["__additional_comments__"]
            ? [
                {
                  clarification: "Additional Comments",
                  answer: answers.current["__additional_comments__"],
                  input_type: "text",
                },
              ]
            : []),
        ],
      }),
    });

    if (res.ok) {
      // Start polling when a new report generation request is sent
      setIsPolling(true);
    } else {
      console.error("Failed to generate report");
    }
  };

  const handleAdditionalComments = (value) => {
    updateAnsweredClarifications("__additional_comments__", value);
  };

  const getFormattedTimezone = () => {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const city = timeZone.split("/")[1]?.replace("_", " ") || timeZone;
    const offset = new Date().getTimezoneOffset();
    const hours = Math.abs(Math.floor(offset / 60));
    const minutes = Math.abs(offset % 60);
    const sign = offset < 0 ? "+" : "-";
    const formattedOffset = `${sign}${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
    return `${city} (UTC${formattedOffset})`;
  };

  const ReportDateTime = ({ date }) => (
    <div className="text-gray-400 dark:text-gray-500 flex items-center space-x-2">
      <span>
        {new Date(date).toLocaleDateString("en-GB", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        })}
      </span>
      <span className="text-gray-300 dark:text-gray-600">•</span>
      <span>
        {new Date(date).toLocaleTimeString("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        })}
      </span>
      <Tooltip title={getFormattedTimezone()} placement="top">
        <InfoCircleOutlined className="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 cursor-help" />
      </Tooltip>
    </div>
  );

  const [hasInitialClarifications, setHasInitialClarifications] = useState(false);
  const questionEditTimer = useRef(null);

  const handleQuestionChange = (e) => {
    const newQuestion = e.target.value;
    setUserQuestion(newQuestion);
    
    // If we already have initial clarifications, auto-trigger on edit after a delay
    if (hasInitialClarifications && newQuestion.length >= 5) {
      if (questionEditTimer.current) {
        clearTimeout(questionEditTimer.current);
      }
      questionEditTimer.current = setTimeout(() => {
        getClarifications();
      }, 1000);
    }
  };

  const handleSendClick = () => {
    if (userQuestion.length >= 5) {
      getClarifications(userQuestion);
      setHasInitialClarifications(true);
    }
  };

  return (
    <>
      <Meta />
      <Scaffolding id="align-model" userType="admin">
        {apiKeyNames.length > 1 ? (
          <Row type={"flex"} height={"100vh"}>
            <Col span={24} style={{ paddingBottom: "1em" }}>
              <Select
                style={{ width: "100%" }}
                onChange={(e) => {
                  setApiKeyName(e);
                }}
                options={apiKeyNames.map((item) => {
                  return { value: item, key: item, label: item };
                })}
                value={apiKeyName}
              />
            </Col>
          </Row>
        ) : null}

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg max-w-3xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold mb-2 dark:text-gray-200">
              The Oracle
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              The Oracle is a background assistant, helping you to dig into your
              dataset for insights. To begin, please let us know what you are
              interested in below.
            </p>
          </div>

          <div className="relative mb-6">
            <TextArea
              placeholder="Describe what you would like the Oracle to do..."
              className="w-full p-3 pr-12 border rounded-lg text-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700 focus:outline-none focus:border-purple-500 dark:focus:border-purple-700"
              value={userQuestion}
              onChange={handleQuestionChange}
              autoSize={{ minRows: 2, maxRows: 10 }}
            />
            <div className="absolute right-3 bottom-3 flex items-center space-x-2">
              {waitClarifications ? (
                <Spin />
              ) : (
                userQuestion &&
                userQuestion.length >= 5 &&
                (!ready ? (
                  <CloseCircleOutlined className="text-red-500" />
                ) : (
                  <CheckCircleOutlined className="text-green-500" />
                ))
              )}
              <button
                onClick={handleSendClick}
                disabled={!userQuestion.trim() || userQuestion.length < 5}
                className={`flex items-center justify-center p-2 rounded-full transition-colors duration-200 ${
                  userQuestion.trim() && userQuestion.length >= 5
                    ? 'text-purple-600 hover:bg-purple-100 dark:text-purple-400 dark:hover:bg-purple-900/30'
                    : 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
                }`}
                title="Send question"
              >
                <SendOutlined className="text-lg" />
              </button>
            </div>
          </div>

          {!ready && readyErrorMsg ? (
            <div className="bg-light-red dark:bg-red-900 p-4 rounded-lg my-2">
              <p className="text-red dark:text-red-400">{readyErrorMsg}</p>
            </div>
          ) : null}

          {clarifications.length > 0 && (
            // show clarifications only when there are some
            <div className="mt-6">
              <h2 className="text-xl font-semibold mb-2 dark:text-gray-200">
                Clarifications
              </h2>
              <TaskType taskType={taskType} onChange={handleTaskTypeChange} />
              {clarifications.map((clarificationObject, index) => (
                <ClarificationItem
                  key={index}
                  clarificationObject={clarificationObject}
                  updateAnsweredClarifications={updateAnsweredClarifications}
                  deleteClarification={() =>
                    deleteClarification(index, clarificationObject)
                  }
                />
              ))}
            </div>
          )}
          {clarifications.length > 0 && (
            <div className="bg-amber-50 dark:bg-amber-900/20 p-4 rounded-lg my-4">
              <div className="text-amber-600 dark:text-amber-400 mb-2 font-medium">
                Additional Comments
              </div>
              <TextArea
                placeholder="Any other thoughts or context you'd like to add?"
                className="w-full dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700"
                autoSize={{ minRows: 2 }}
                onChange={(e) => handleAdditionalComments(e.target.value)}
                value={answers.current["__additional_comments__"] || ""}
              />
            </div>
          )}

          <div className="mt-6">
            <Sources sources={sources} setSources={setSources} />
          </div>

          <Button
            className="bg-purple-500 text-white py-4 px-4 mt-2 mb-2 rounded-lg hover:bg-purple-600 disabled:bg-gray-300 dark:disabled:bg-gray-700 dark:hover:bg-purple-700"
            onClick={generateReport}
            disabled={userQuestion.length < 5 || taskType === ""}
          >
            Generate
          </Button>
        </div>

        <div>
          <h2 className="text-2xl font-semibold mb-4 dark:text-gray-200">
            Past Reports
          </h2>
          {reports.map((report, index) => (
            <div
              key={index}
              className="bg-purple-100 dark:bg-purple-900/30 shadow-lg rounded-lg mb-4 overflow-hidden border border-purple-200 dark:border-purple-800 hover:border-purple-300 dark:hover:border-purple-700 transition-all"
            >
              <div className="p-4">
                {report.report_name ? (
                  <>
                    <h3 className="text-lg font-semibold text-purple-700 dark:text-purple-400 mb-1">
                      {report.report_name}
                    </h3>
                    <div className="text-base mb-3 flex items-center justify-between">
                      <div className="text-gray-500 dark:text-gray-400 flex items-center">
                        <FileTextOutlined className="mr-1" />
                        <span>{String(report.report_id).padStart(3, "0")}</span>
                      </div>
                      <ReportDateTime date={report.date_created} />
                    </div>
                  </>
                ) : (
                  <div className="mb-3">
                    <div className="text-base flex items-center justify-between">
                      <div className="text-gray-700 dark:text-gray-300 font-semibold flex items-center">
                        <FileTextOutlined className="mr-2" />
                        <span>{report?.inputs?.user_question}</span>
                      </div>
                      <ReportDateTime date={report.date_created} />
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <ReportStatus status={report.status} />
                  </div>
                  <div className="flex items-center space-x-2">
                    {report.status === "done" && (
                      <>
                        <Button
                          className="text-purple-700 hover:text-purple-900 dark:text-purple-400 dark:hover:text-purple-300"
                          onClick={() =>
                            window.open(
                              `/view-oracle-report?reportId=${report.report_id}&keyName=${apiKeyName}`,
                              "_blank"
                            )
                          }
                        >
                          View Report
                        </Button>
                        {/* <Button
                          className="text-purple-700 hover:text-purple-900 dark:text-purple-400 dark:hover:text-purple-300"
                          onClick={() => downloadReport(report.report_id)}
                        >
                          Download
                        </Button> */}
                      </>
                    )}
                    {(report.status === "done" ||
                      report.status === "error") && (
                      <Button
                        className="text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400 transition-colors"
                        icon={<DeleteOutlined />}
                        onClick={() => deleteReport(report.report_id)}
                      />
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Scaffolding>
    </>
  );
}

function ClarificationItem({
  clarificationObject,
  updateAnsweredClarifications,
  deleteClarification,
}) {
  const [selectedChoice, setSelectedChoice] = useState(null);

  const otherSelected = useMemo(
    () => (selectedChoice || "").toLowerCase() === "other",
    [selectedChoice]
  );

  const opts = clarificationObject.options;
  // add an other option if it doesn't exist and the input type is single_choice
  if (
    clarificationObject.input_type === "single_choice" &&
    opts.indexOf("Other") === -1 &&
    opts.indexOf("other") === -1
  ) {
    opts.push("Other");
  }

  return (
    <div className="bg-amber-100 dark:bg-amber-900/30 p-4 rounded-lg my-2 relative flex flex-row">
      <div className="text-amber-500 dark:text-amber-400 w-3/4">
        {clarificationObject.clarification}
      </div>
      <div className="w-1/4 mt-2 mx-2">
        {clarificationObject.input_type === "single_choice" ? (
          <div>
            <Select
              allowClear={true}
              className="flex w-5/6 dark:bg-gray-800 dark:text-gray-200"
              optionRender={(opt, info) => (
                <div className="text-wrap break-words hyphens-auto dark:text-gray-200">
                  {opt.label}
                </div>
              )}
              onChange={(value) => {
                setSelectedChoice(value);
                updateAnsweredClarifications(
                  clarificationObject.clarification,
                  value,
                  true
                );
              }}
              options={opts.map((option) => ({
                value: option,
                label: option,
              }))}
            />
            {/* if other is selected, show a text input too */}
            {otherSelected ? (
              <TextArea
                placeholder="Type here"
                className="my-2 w-5/6 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700"
                autoSize={true}
                onChange={(value) => {
                  // if this is empty, then just set answer back to to selectedOption
                  if (value.target.value === "") {
                    updateAnsweredClarifications(
                      clarificationObject.clarification,
                      selectedChoice || null
                    );
                  } else {
                    // else set answer to the value of this text area
                    updateAnsweredClarifications(
                      clarificationObject.clarification,
                      value.target.value
                    );
                  }
                }}
              />
            ) : null}
          </div>
        ) : clarificationObject.input_type === "multiple_choice" &&
          clarificationObject?.options?.length ? (
          <Checkbox.Group
            className="flex w-5/6"
            options={clarificationObject.options.map((option) => ({
              label: option,
              value: option,
            }))}
            onChange={(value) =>
              updateAnsweredClarifications(
                clarificationObject.clarification,
                value
              )
            }
          />
        ) : (
          <TextArea
            autoSize={true}
            className="flex w-5/6 rounded-lg dark:bg-gray-800 dark:text-gray-200 dark:border-gray-700"
            onChange={(value) =>
              updateAnsweredClarifications(
                clarificationObject.clarification,
                value.target.value
              )
            }
          />
        )}
      </div>
      <CloseOutlined
        className="text-amber-500 dark:text-amber-400 absolute top-2 right-2 cursor-pointer"
        onClick={deleteClarification}
      />
    </div>
  );
}

export default OracleDashboard;
