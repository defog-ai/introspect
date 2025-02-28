"use client";
import { useEffect, useState } from "react";
import { OracleEmbed } from "@defogdotai/agents-ui-components/oracle";
import Scaffolding from "$components/layout/Scaffolding";
import Meta from "$components/layout/Meta";
import { SpinningLoader } from "@defogdotai/agents-ui-components/core-ui";

// Main Component
export default function OracleDashboard() {
  const [token, setToken] = useState<string>("");
  const [userType, setUserType] = useState<string>("");
  const [dbNames, setDbNames] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const getApiKeyNames = async () => {
    const token = localStorage.getItem("defogToken");
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_db_names",
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
    setDbNames(data.db_names);
    setLoading(false);
  };

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    const userType = localStorage.getItem("defogUserType");
    setUserType(userType);
    setToken(token);
    getApiKeyNames();
    if (token) setToken(token);
  }, []);

  return (
    (loading === true) ? 
    <SpinningLoader/>
    :
    <div className="h-screen">
      <Meta />
      <Scaffolding
        id={"query-data"}
        userType={userType}
        containerClassNames="max-h-screen h-screen flex flex-col"
        contentClassNames="h-full max-h-full"
      >
        <OracleEmbed
          apiEndpoint={process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}
          token={token}
          initialDbNames={dbNames}
        />
      </Scaffolding>
    </div>
  )
}
