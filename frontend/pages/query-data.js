import React, { useState, useEffect } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import dynamic from "next/dynamic";
// import { DefogAnalysisAgentStandalone } from "$agents-ui-components";

const DefogAnalysisAgentStandalone = dynamic(
  () =>
    import("$agents-ui-components").then((module) => {
      return module.DefogAnalysisAgentStandalone;
    }),
  {
    ssr: false,
  }
);

const QueryDatabase = () => {
  const [token, setToken] = useState("");
  const [user, setUser] = useState("");
  const [userType, setUserType] = useState("");
  const [devMode, setDevMode] = useState(false);
  // const [queryMode, setQueryMode] = useState("agents");

  const apiKeyNames = (
    process.env.NEXT_PUBLIC_API_KEY_NAMES || "REPLACE_WITH_API_KEY_NAMES"
  ).split(",");
  const [apiKeyName, setApiKeyName] = useState(apiKeyNames[0]);

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    const userType = localStorage.getItem("defogUserType");
    const user = localStorage.getItem("defogUser");
    setUser(user);
    setUserType(userType);
    setToken(token);
  }, []);

  return (
    <>
      <Meta />
      <Scaffolding id={"query-data"} userType={userType}>
        {/* {apiKeyNames.length > 1 ? (
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
        <h1>Query your database</h1>
        {userType === "admin" ? (
          <Switch
            checkedChildren="Production"
            unCheckedChildren="Development"
            checked={!devMode}
            onChange={(e) => {
              setDevMode(!e);
            }}
          />
        ) : null} */}
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
            keyName={apiKeyName}
          />
        ) : null}
      </Scaffolding>
    </>
  );
};

export default QueryDatabase;
