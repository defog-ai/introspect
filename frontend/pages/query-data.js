"use-client";
import React, { useState, useEffect } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import {
  MessageManager,
  MessageManagerContext,
  MessageMonitor,
  SingleSelect,
  Toggle,
} from "$ui-components";
import { DefogAnalysisAgentStandalone } from "$agents-ui-components";

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
      <Scaffolding
        id={"query-data"}
        userType={userType}
        rootClassNames="h-screen"
      >
        <div className="flex flex-col h-full">
          <div className="flex flex-row gap-4 items-start justify-center border-b p-2">
            {apiKeyNames.length > 1 ? (
              <SingleSelect
                label={"Database"}
                rootClassNames="w-48"
                onChange={(e) => {
                  setApiKeyName(e);
                }}
                options={apiKeyNames.map((item) => {
                  return { value: item, key: item, label: item };
                })}
                defaultValue={apiKeyName}
                allowClear={false}
              />
            ) : null}
            {userType === "admin" ? (
              <Toggle
                rootClassNames="w-32"
                title={"Environment"}
                onLabel="Production"
                offLabel="Development"
                defaultOn={!devMode}
                onToggle={(e) => {
                  setDevMode(!e);
                }}
              />
            ) : null}
          </div>

          {token ? (
            <MessageManagerContext.Provider value={MessageManager()}>
              <MessageMonitor />
              <DefogAnalysisAgentStandalone
                rootClassNames="grow"
                devMode={devMode}
                token={token}
                apiEndpoint={process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}
                keyName={apiKeyName}
                predefinedQuestions={["Show me 5 rows"]}
              />
            </MessageManagerContext.Provider>
          ) : null}
        </div>
      </Scaffolding>
    </>
  );
};

export default QueryDatabase;
