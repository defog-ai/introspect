import { Button, Input, Row, Col, Select, Spin, Checkbox } from "antd";
import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import Sources from "$components/oracle/Sources";
import TaskType from "$components/oracle/TaskType";
import setupBaseUrl from "$utils/setupBaseUrl";
import { useRouter } from "next/router";
import {
  CheckCircleOutlined,
  CloseOutlined,
  DownloadOutlined,
  DeleteOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";

const { TextArea } = Input;

function OracleDashboard() {
  const [apiKeyName, setApiKeyName] = useState(null);
  const [apiKeyNames, setApiKeyNames] = useState([]);

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
  const [ready, setReady] = useState(false);
  const [readyErrorMsg, setReadyErrorMsg] = useState("");
  const [userQuestion, setUserQuestion] = useState("");

  const answers = useRef({});
  const [clarifications, setClarifications] = useState([]);
  const [answerLastUpdateTs, setAnswerLastUpdateTs] = useState(Date.now());
  const [waitClarifications, setWaitClarifications] = useState(false);
  const [taskType, setTaskType] = useState(null);
  const [sources, setSources] = useState([]);
  const [waitSources, setWaitSources] = useState(false);
  const [reports, setReports] = useState([]);

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
      setTaskType(data.task_type);
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
    // remove the clarification from the list of clarifications
    setClarifications((prevClarifications) =>
      prevClarifications.filter((_, i) => i !== index)
    );

    // remove from answers
    answers.current[clarificationObject.clarification] = undefined;
  };

  const getSources = async () => {
    setWaitSources(true);
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
    setWaitSources(false);
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

  useEffect(() => {
    const token = localStorage.getItem("defogToken");

    const pollReports = async () => {
      try {
        const res = await fetch(setupBaseUrl("http", `oracle/list_reports`), {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token: token,
            key_name: apiKeyName,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          setReports(data.reports);
        } else {
          console.error("Failed to fetch reports");
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("An error occurred:", error);
        clearInterval(intervalId);
      }
    };

    const intervalId = setInterval(pollReports, 1000);

    // Optionally, start the first poll immediately
    pollReports();

    return () => clearInterval(intervalId);
  }, [apiKeyName]);

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
    // delete a report
    const token = localStorage.getItem("defogToken");
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
  };

  const generateReport = async () => {
    // generate a report
    const token = localStorage.getItem("defogToken");
    const selectedSources = sources.filter((source) => source.selected);
    console.log("Selected sources:", selectedSources);

    //

    const res = await fetch(setupBaseUrl("http", `oracle/begin_generation`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token,
        key_name: apiKeyName,
        user_question: userQuestion,
        sources: selectedSources,
        task_type: taskType,
        clarifications: clarifications.map((d) => ({
          ...d,
          answer: answers.current[d.clarification],
        })),
      }),
    });
  };

  useEffect(() => {
    // after 2000ms, get clarifications
    const timeout = setTimeout(() => {
      // fetch clarifications as the user is typing
      if (userQuestion.length < 5) {
        console.log("User task is too short, not fetching clarifications yet");
      } else {
        // when doing this, clear the answers
        answers.current = {};
        getClarifications();
        getSources();
      }
    }, 2000);

    return () => clearTimeout(timeout);

    // the effect runs shortly after userQuestion changes
  }, [userQuestion]);

  useEffect(() => {
    // after 1000ms, get clarifications
    const timeout = setTimeout(() => {
      getClarifications();
    }, 1000);

    return () => clearTimeout(timeout);

    // the effect runs shortly only when answerLastUpdateTs changes
    // i.e. when the user answers a clarification
  }, [answerLastUpdateTs]);

  useEffect(() => {
    if (!apiKeyName) return;
    // check DB / backend API readiness
    checkReady();

    // the effect runs after the apiKeyName fetches / changes as our checks
    // depend on the api key
  }, [apiKeyName]);

  // console.log(apiKeyName, reports);

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

        <div className="bg-white p-6 rounded-lg shadow-lg max-w-3xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold mb-2">The Oracle</h1>
            <p className="text-gray-600">
              The Oracle is a background assistant, helping you to dig into your
              dataset for insights. To begin, please let us know what you are
              interested in below.
            </p>
          </div>

          <div className="flex items-center mb-6">
            <TextArea
              placeholder="Describe what you would like the Oracle to do..."
              className="w-full p-3 border rounded-lg text-gray-700 focus:outline-none focus:border-purple-500"
              value={userQuestion}
              onChange={(e) => {
                setUserQuestion(e.target.value);
                // let the user type a few characters before fetching clarifications
              }}
              autoSize={{ minRows: 2, maxRows: 10 }}
              style={{ flexBasis: "90%" }}
            />
            <div className="ml-2">
              {waitClarifications ? (
                <Spin />
              ) : (
                userQuestion &&
                userQuestion.length >= 5 &&
                (!ready ? (
                  <CloseCircleOutlined style={{ color: "#b80617" }} />
                ) : (
                  <CheckCircleOutlined style={{ color: "green" }} />
                ))
              )}
            </div>
          </div>

          {!ready && readyErrorMsg ? (
            <div className="bg-light-red p-4 rounded-lg my-2">
              <p className="text-red">{readyErrorMsg}</p>
            </div>
          ) : null}

          {clarifications.length > 0 && (
            // show clarifications only when there are some
            <div className="mt-6">
              <h2 className="text-xl font-semibold mb-2">Clarifications</h2>
              <TaskType taskType={taskType} />
              {clarifications.map((clarificationObject, index) => (
                <ClarificationItem
                  key={String(clarificationObject.clarification)}
                  clarificationObject={clarificationObject}
                  updateAnsweredClarifications={updateAnsweredClarifications}
                  deleteClarification={() =>
                    deleteClarification(index, clarificationObject)
                  }
                />
              ))}
            </div>
          )}

          <div className="mt-6">
            <Sources sources={sources} setSources={setSources} />
          </div>

          <Button
            className="bg-purple-500 text-white py-4 px-4 mt-2 mb-2 rounded-lg hover:bg-purple-600 disabled:bg-gray-300"
            onClick={generateReport}
            disabled={userQuestion.length < 5 || taskType === ""}
          >
            Generate
          </Button>
        </div>

        <div>
          <h2 className="text-xl font-semibold mb-4">Past Reports</h2>
          {reports.map((report, index) => (
            <div key={index} className="bg-purple-100 p-4 rounded-lg mb-4">
              <h3 className="text-lg font-semibold">{report.report_id}</h3>
              <p className="text-purple-700">{report.report_name}</p>
              <p className="text-gray-600">{report.status}</p>
              <p className="text-gray-400">
                Generated at {report.date_created}
              </p>
              <div className="flex space-x-4 mt-2">
                <Button
                  className="text-purple-700 fill-purple-200 hover:text-purple-900 disabled:text-gray-300"
                  icon={<DownloadOutlined />}
                  disabled={report.status !== "done"}
                  onClick={() => downloadReport(report.report_id)}
                >
                  Download PDF
                </Button>
                <Button
                  className="text-purple-700 fill-purple-200 hover:text-purple-900 disabled:text-gray-300"
                  disabled={report.status !== "done"}
                  onClick={() =>
                    router.push({
                      pathname: "view-oracle-report",
                      query: {
                        reportId: report.report_id,
                        keyName: apiKeyName,
                      },
                    })
                  }
                >
                  View
                </Button>
                <Button
                  className="text-purple-700 fill-purple-200 hover:text-purple-900 disabled:text-gray-300"
                  icon={<DeleteOutlined />}
                  disabled={
                    report.status !== "done" && report.status !== "error"
                  }
                  onClick={() => deleteReport(report.report_id)}
                >
                  Delete
                </Button>
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
    <div className="bg-amber-100 p-4 rounded-lg my-2 relative flex flex-row">
      <div className="text-amber-500 w-3/4">
        {clarificationObject.clarification}
      </div>
      <div className="w-1/4 mt-2 mx-2">
        {clarificationObject.input_type === "single_choice" ? (
          <div>
            <Select
              allowClear={true}
              className="flex w-5/6"
              optionRender={(opt, info) => (
                <div className="text-wrap break-words hyphens-auto">
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
                className="my-2 w-5/6"
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
        ) : clarificationObject.input_type === "multiple_choice" ? (
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
            className="flex w-5/6 rounded-lg"
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
        className="text-amber-500 absolute top-2 right-2 cursor-pointer"
        onClick={deleteClarification}
      />
    </div>
  );
}

export default OracleDashboard;
