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
import { QueryData } from "$components/agents/QueryData";

const QueryDataPage = () => {
  const [token, setToken] = useState("");
  const [user, setUser] = useState("");
  const [userType, setUserType] = useState("");
  const [devMode, setDevMode] = useState(false);

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
        rootClassNames="h-screen relative"
      >
        <div className="flex flex-col h-full">
          {/* <div className=""> */}
          {userType === "admin" ? (
            <Toggle
              rootClassNames="mx-auto p-2 absolute lg:fixed w-44 border bg-white rounded-md left-0 right-0 mx-auto top-2 lg:bottom-0 lg:top-auto lg:right-auto lg:shadow-md z-50"
              title={"Environment"}
              onLabel="Production"
              offLabel="Development"
              defaultOn={!devMode}
              onToggle={(e) => {
                setDevMode(!e);
              }}
            />
          ) : null}
          {/* </div> */}

          {token ? (
            <MessageManagerContext.Provider value={MessageManager()}>
              <MessageMonitor />
              {/* env keyname stuff happens inside QueryData component */}
              <QueryData
                devMode={devMode}
                token={token}
                apiEndpoint={process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}
                predefinedQuestions={["Show me 5 rows"]}
              />
            </MessageManagerContext.Provider>
          ) : null}
        </div>
      </Scaffolding>
    </>
  );
};

export default QueryDataPage;
