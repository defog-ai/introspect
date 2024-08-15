import { Button, Input, Row, Col, Select, Spin } from "antd";
import { useState, useEffect } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import setupBaseUrl from "$utils/setupBaseUrl";
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseOutlined,
} from "@ant-design/icons";

function OracleDashboard() {
  const apiKeyNames = (
    process.env.NEXT_PUBLIC_API_KEY_NAMES || "REPLACE_WITH_API_KEY_NAMES"
  ).split(",");
  const [apiKeyName, setApiKeyName] = useState(apiKeyNames[0]);
  const [userTask, setUserTask] = useState("");
  const [clarifications, setClarifications] = useState([]);
  const [waitClarifications, setWaitClarifications] = useState(false);
  const [ready, setReady] = useState(false);
  const [reports, setReports] = useState([]);

  const getClarifications = async () => {
    // fetch clarifications as the user is typing
    if (userTask.length < 5) {
      console.log("User task is too short, not fetching clarifications yet");
      return;
    }
    setWaitClarifications(true);
    const token = localStorage.getItem("defogToken");
    const res = await fetch(
      setupBaseUrl("http", `oracle/clarify_formulation`),
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
    setWaitClarifications(false);
    if (res.ok) {
      const data = await res.json();
      // we have the following fields to set:
      // - data.clarifications [list of string]
      // - data.ready [bool]
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

  const getReports = async () => {
    // fetch reports
    const token = localStorage.getItem("defogToken");
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
    }
  };

  const generateReport = async () => {
    // generate a report
    const token = localStorage.getItem("defogToken");
    const res = await fetch(setupBaseUrl("http", `oracle/generate_report`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token,
        user_task: userTask,
      }),
    });

    if (res.ok) {
      const data = await res.json();

      // for now, we just log the data
      // later, we can do something more useful with it
      console.log(data);
    }
  };

  useEffect(() => {
    // after 3000ms, get clarifications
    const timeout = setTimeout(() => {
      getClarifications();
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
                defaultValue={apiKeyName}
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
              {clarifications.map((clarification, index) => (
                <div
                  key={index}
                  className="bg-amber-100 p-4 rounded-lg mb-4 relative"
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

          <Button
            className="bg-purple-500 text-white py-2 px-4 rounded-lg hover:bg-purple-600"
            disabled={!ready}
            onClick={generateReport}
          >
            Generate
          </Button>
        </div>

        <div>
          <h2 className="text-xl font-semibold mb-4">Past Reports</h2>
          {reports.map((report, index) => (
            <div key={index} className="bg-purple-100 p-4 rounded-lg mb-4">
              <p className="text-purple-700">{report.report_name}</p>
              <p className="text-gray-500">
                {report.status === "generating"
                  ? "Report generating..."
                  : `Report generated on ${report.date_created}`}
              </p>
              <div className="flex space-x-4">
                <button className="text-purple-700 hover:text-purple-900">
                  Download
                </button>
                <button className="text-purple-700 hover:text-purple-900">
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
