"use client";
import React, { useState, useEffect } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import { Toggle } from "@defogdotai/agents-ui-components/core-ui";

import { TestDrive } from "$components/TestDrive";

const QueryDataPage = () => {
  const [token, setToken] = useState("");
  const [user, setUser] = useState("");
  const [userType, setUserType] = useState("");
  const [devMode, setDevMode] = useState(false);
  const [apiKeyNames, setApiKeyNames] = useState(["Default DB"]);

  const getApiKeyNames = async (token) => {
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_api_key_names",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
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
  };

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    const userType = localStorage.getItem("defogUserType");
    const user = localStorage.getItem("defogUser");
    setUser(user);
    setUserType(userType);
    setToken(token);

    getApiKeyNames(token);
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
            <>
              <TestDrive
                token={token}
                devMode={devMode}
                dbs={(apiKeyNames.length > 0
                  ? apiKeyNames
                  : ["Default DB"]
                ).map((name) => {
                  return {
                    name: name,
                    keyName: name,
                    predefinedQuestions:
                      name === "Manufacturing"
                        ? [
                            "What is the average rejection rate by lot?",
                            "Is there a difference in the plasticity of components that are rejected vs accepted?",
                          ]
                        : name === "Sales"
                          ? [
                              "Who are our top 5 customers by revenue?",
                              "What was the month on month change in revenue?",
                            ]
                          : name === "Slack"
                            ? [
                                "What is the count of number of queries by db type in the last 30 days, except for queries made by jp@defog.ai?",
                                "Which users have the most queries?",
                              ]
                            : ["Show me any 5 rows from the first table"],
                  };
                })}
              />
            </>
          ) : null}
        </div>
      </Scaffolding>
    </>
  );
};

export default QueryDataPage;
