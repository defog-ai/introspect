"use client";
import React, { useState, useEffect } from "react";
import Meta from "$components/layout/Meta";
import Scaffolding from "$components/layout/Scaffolding";
import {
  SpinningLoader,
  Toggle,
} from "@defogdotai/agents-ui-components/core-ui";
import { TestDrive } from "$components/TestDrive";

const QueryDataPage = () => {
  const [token, setToken] = useState("");
  const [user, setUser] = useState("");
  const [userType, setUserType] = useState("");
  const [apiKeyNames, setApiKeyNames] = useState(["Default DB"]);
  const [loading, setLoading] = useState(false);

  const [nonAdminConfig, setNonAdminConfig] = useState({});

  const getApiKeyNames = async (token) => {
    setLoading(true);
    let res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_db_names",
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
      setLoading(false);
      throw new Error(
        "Failed to get api key names - are you sure your network is working?"
      );
    }
    let data = await res.json();
    setApiKeyNames(data.db_names);

    res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_non_admin_config",
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
      setLoading(false);
      throw new Error(
        "Failed to get non admin config - are you sure your network is working?"
      );
    }

    data = await res.json();
    setNonAdminConfig(data);

    setLoading(false);
  };

  console.log(nonAdminConfig);

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    const userType = localStorage.getItem("defogUserType");
    const user = localStorage.getItem("defogUser");
    setUser(user);
    setUserType(userType);
    setToken(token);

    getApiKeyNames(token);
  }, []);

  const isAdmin = userType === "admin";

  return (
    <div className="max-h-screen h-screen">
      <Meta />
      <Scaffolding
        id={"query-data"}
        userType={userType}
        containerClassNames="max-h-screen h-screen flex flex-col"
        contentClassNames="h-full max-h-full"
      >
        {token ? (
          loading ? (
            <div className="w-full h-full flex justify-center items-center text-gray-400 text-sm">
              Loading DBs <SpinningLoader classNames="ml-4" />
            </div>
          ) : (
            <TestDrive
              token={token}
              devMode={false}
              isAdmin={isAdmin}
              hideSqlTab={
                isAdmin ? false : nonAdminConfig.hide_sql_tab_for_non_admin
              }
              hidePreviewTabs={
                isAdmin ? false : nonAdminConfig.hide_preview_tabs_for_non_admin
              }
              hiddenCharts={
                isAdmin ? [] : nonAdminConfig.hidden_charts_for_non_admin || []
              }
              hideRawAnalysis={
                isAdmin ? false : nonAdminConfig.hide_raw_analysis_for_non_admin
              }
              dbs={(apiKeyNames.length > 0 ? apiKeyNames : ["Default DB"]).map(
                (name) => {
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
                }
              )}
            />
          )
        ) : (
          <div className="w-full h-full flex justify-center items-center text-gray-400 text-sm">
            No token found. Please log out and log back in.
          </div>
        )}
      </Scaffolding>
    </div>
  );
};

export default QueryDataPage;
