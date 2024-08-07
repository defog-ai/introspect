import { useState, useEffect } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import setupBaseUrl from "$utils/setupBaseUrl";

function OracleDashboard() {
  const [reports, setReports] = useState([
    {
      name: "Report 1",
      status: "generating",
      date: "",
    },
    {
      name: "Report 2",
      status: "generated",
      date: "2024-08-01",
    },
    {
      name: "Report 3",
      status: "generated",
      date: "2024-08-02",
    },
  ]);
  const [userTask, setUserTask] = useState("");

  const getReports = async () => {
    // fetch reports
    const token = localStorage.getItem("defogToken");
    const res = await fetch(setupBaseUrl("http", `oracle/get_reports`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token,
      }),
    });

    if (res.ok) {
      const data = await res.json();
      setReports(data.reports);
    }
  };

  const getClarifications = async () => {
    // fetch clarifications as the user is typing
    if (userTask.length < 5) {
      console.log("User task is too short, not fetching clarifications yet");
      return;
    }

    const token = localStorage.getItem("defogToken");
    const res = await fetch(setupBaseUrl("http", `oracle/get_clarifications`), {
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
    } else {
      console.error("Failed to fetch clarifications");
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
    // after 5000ms, get clarifications
    const timeout = setTimeout(() => {
      getClarifications();
    }, 5000);

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
        <div className="bg-white p-6 rounded-lg shadow-lg max-w-3xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold mb-2">The Oracle</h1>
            <p className="text-gray-600">
              The Oracle is a background assistant, helping you to dig into your
              dataset for insights. To begin, please let us know what you are
              interested in below.
            </p>
          </div>

          <div className="mb-6">
            <input
              type="text"
              placeholder="Describe what you would like the Oracle to do..."
              className="w-full p-3 border rounded-lg text-gray-700 focus:outline-none focus:border-purple-500"
              value={userTask}
              onChange={(e) => {
                setUserTask(e.target.value);
                // let the user type a few characters before fetching clarifications
              }}
            />
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-2">Options</h2>
            <div className="flex items-center mb-4">
              <input type="checkbox" id="email" className="mr-2" />
              <label htmlFor="email" className="text-gray-700">
                Email
              </label>
            </div>

            <div className="flex items-center mb-6">
              <input type="checkbox" id="bucketStorage" className="mr-2" />
              <label htmlFor="bucketStorage" className="text-gray-700">
                bucket storage
              </label>
            </div>

            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center">
                <span className="text-gray-700 mr-2">Process latest data</span>
                <input type="checkbox" className="toggle-checkbox" checked />
              </div>

              <div className="flex items-center">
                <span className="text-gray-700 mr-2">Recurring</span>
                <input type="checkbox" className="toggle-checkbox" checked />
              </div>
            </div>

            <button
              className="bg-purple-500 text-white py-2 px-4 rounded-lg hover:bg-purple-600"
              onClick={generateReport}
            >
              Generate
            </button>
          </div>

          <div>
            <h2 className="text-xl font-semibold mb-4">Past Reports</h2>
            {reports.map((report, index) => (
              <div key={index} className="bg-purple-100 p-4 rounded-lg mb-4">
                <p className="text-purple-700">{report.name}</p>
                <p className="text-gray-500">
                  {report.status === "generating"
                    ? "Report generating..."
                    : `Report generated on ${report.date}`}
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
        </div>
      </Scaffolding>
    </>
  );
}

export default OracleDashboard;
