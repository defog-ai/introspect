import React, { useState, useEffect, useContext } from "react";
import Meta from "$components/common/Meta";
import dynamic from "next/dynamic";
import { Switch } from "antd/lib";
import setupBaseUrl from "$utils/setupBaseUrl";

const DefogAnalysisAgentStandalone = dynamic(
  () =>
    import(
      "$components/defog-components/components/DefogAnalysisAgentStandalone"
    ).then((module) => {
      return module.default;
    }),
  {
    ssr: false,
  }
);

const Test = () => {
  const [selectedTables, setSelectedTables] = useState([]);
  const [token, setToken] = useState();
  const [user, setUser] = useState();
  const [userType, setUserType] = useState();
  const [devMode, setDevMode] = useState(false);
  // const [queryMode, setQueryMode] = useState("agents");

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    const userType = localStorage.getItem("defogUserType");
    const user = localStorage.getItem("defogUser");
    setUser(user);
    setUserType(userType);
    setToken(token);
    const res = fetch(setupBaseUrl("http", "integration/get_tables_db_creds"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ token: token }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.selected_tables) {
          setSelectedTables(data.selected_tables);
        }
      });
  }, []);

  return (
    <div className="">
      <Meta />
      <h1>Query your database</h1>
      <p>
        Ask Defog questions about your data. You have selected the following
        tables: <code>{selectedTables.join(", ")}</code>
      </p>
      {userType === "admin" ? (
        <Switch
          checkedChildren="Production"
          unCheckedChildren="Development"
          checked={!devMode}
          onChange={(e) => {
            setDevMode(!e);
          }}
        />
      ) : null}
      {/* <Switch
          checkedChildren="SQL"
          unCheckedChildren="Agents"
          checked={queryMode === "sql"}
          onChange={(e) => {
            setQueryMode(e ? "sql" : "agents");
          }}
        /> */}
      {token ? (
        <DefogAnalysisAgentStandalone
          analysisId={null}
          token={token}
          devMode={devMode}
        />
      ) : null}
    </div>
  );
};

export default Test;
