import { Button, Input, Row, Col, Select, Spin } from "antd";
import { useState, useEffect } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import Sources from "$components/oracle/Sources";
import TaskType from "$components/oracle/TaskType";
import setupBaseUrl from "$utils/setupBaseUrl";
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseOutlined,
} from "@ant-design/icons";

function OracleDashboard() {
  const [apiKeyNames, setApiKeyNames] = useState([]);

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
  const [apiKeyName, setApiKeyName] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    getApiKeyNames(token);
  }, []);
  const [userTask, setUserTask] = useState("");
  const [clarifications, setClarifications] = useState([]);
  const [waitClarifications, setWaitClarifications] = useState(false);
  const [taskType, setTaskType] = useState("");
  const [sources, setSources] = useState([]);
  const [waitSources, setWaitSources] = useState(false);
  const [ready, setReady] = useState(false);
  const [reports, setReports] = useState([]);

  const getClarifications = async () => {
    setWaitClarifications(true);
    const token = localStorage.getItem("defogToken");
    const res = await fetch(setupBaseUrl("http", `oracle/clarify_question`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token: token,
        key_name: apiKeyName,
        question: userTask,
      }),
    });
    setWaitClarifications(false);
    if (res.ok) {
      const data = await res.json();
      // we have the following fields to set:
      // - data.clarifications [list of string]
      // - data.task_type [string]
      // - data.ready [bool]
      setTaskType(data.task_type);
      setClarifications(data.clarifications);
      setReady(data.ready);
    } else {
      console.error("Failed to fetch clarifications");
    }
  };

  const deleteClarification = (index) => {
    setClarifications((prevClarifications) =>
      prevClarifications.filter((_, i) => i !== index)
    );
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
          question: userTask,
        }),
      }
    );
    setWaitSources(false);
    if (res.ok) {
      const data = await res.json();
      // we only use the list of organic search results, discarding the rest for now
      const sources = data.organic;
      // add a selected field to each source
      sources.forEach((source) => {
        source.selected = false;
      });
      setSources(sources);
    } else {
      console.error("Failed to fetch sources");
    }
  };

  // function that checks if status == done or error for each report
  const checkAllFinished = (reports) => {
    return reports.every(
      (report) => report.status === "done" || report.status === "error"
    );
  };

  const getReports = async () => {
    const token = localStorage.getItem("defogToken");
    let allFinished = false;

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
          allFinished = checkAllFinished(data.reports);

          if (allFinished) {
            clearInterval(intervalId);
          }
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
  };

  const deleteReport = async (index) => {
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
        report_id: reports[index].report_id,
      }),
    });

    if (res.ok) {
      // call getReports to refresh the list
      getReports();
    }
  };

  const generateReport = async () => {
    // generate a report
    const token = localStorage.getItem("defogToken");
    const selectedSources = sources.filter((source) => source.selected);
    console.log(selectedSources);
    const res = await fetch(setupBaseUrl("http", `oracle/begin_generation`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token,
        key_name: apiKeyName,
        question: userTask,
        sources: selectedSources,
        task_type: taskType,
      }),
    });

    if (res.ok) {
      // at this point, we should have the new report's as an entry in the DB already
      getReports();
    }
  };

  useEffect(() => {
    // after 3000ms, get clarifications
    const timeout = setTimeout(() => {
      // fetch clarifications as the user is typing
      if (userTask.length < 5) {
        console.log("User task is too short, not fetching clarifications yet");
      } else {
        getClarifications();
        getSources();
      }
    }, 3000);

    return () => clearTimeout(timeout);

    // the effect runs whenever userTask changes
  }, [userTask]);

  useEffect(() => {
    // get reports when the component mounts
    getReports();

    // the effect runs only once, and does not depend on any state
  }, []);

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
            <Input.TextArea
              placeholder="Describe what you would like the Oracle to do..."
              className="w-full p-3 border rounded-lg text-gray-700 focus:outline-none focus:border-purple-500"
              value={userTask}
              onChange={(e) => {
                setUserTask(e.target.value);
                // let the user type a few characters before fetching clarifications
              }}
              autoSize={{ minRows: 2, maxRows: 10 }}
              style={{ flexBasis: "90%" }}
            />
            <div className="ml-2">
              {waitClarifications ? (
                <Spin />
              ) : (
                userTask &&
                (ready ? (
                  <CheckCircleOutlined style={{ color: "green" }} />
                ) : (
                  <ExclamationCircleOutlined style={{ color: "#808080" }} />
                ))
              )}
            </div>
          </div>

          {clarifications.length > 0 && (
            // show clarifications only when there are some
            <div className="mt-6">
              <h2 className="text-xl font-semibold mb-2">Clarifications</h2>
              <TaskType taskType={taskType} />
              {clarifications.map((clarification, index) => (
                <div
                  key={index}
                  className="bg-amber-100 p-4 rounded-lg my-2 relative"
                >
                  <p className="text-amber-500">{clarification}</p>
                  <CloseOutlined
                    className="text-amber-500 absolute top-2 right-2 cursor-pointer"
                    onClick={() => deleteClarification(index)}
                  />
                </div>
              ))}
            </div>
          )}

          <div className="mt-6">
            <Sources sources={sources} setSources={setSources} />
          </div>

          <Button
            className="bg-purple-500 text-white py-4 px-4 mt-2 mb-2 rounded-lg hover:bg-purple-600 disabled:bg-gray-300"
            onClick={generateReport}
            disabled={userTask.length < 5 || taskType === ""}
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
              <div className="flex space-x-4">
                <button className="text-purple-700 hover:text-purple-900">
                  Download
                </button>
                <button
                  className="text-purple-700 hover:text-purple-900"
                  onClick={() => deleteReport(index)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </Scaffolding>
    </>
  );
}

export default OracleDashboard;
