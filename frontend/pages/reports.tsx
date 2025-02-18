"use client";
import { useEffect, useState } from "react";
import { OracleEmbed } from "@defogdotai/agents-ui-components/oracle";
import Scaffolding from "$components/layout/Scaffolding";
import Meta from "$components/layout/Meta";

// Main Component
export default function OracleDashboard() {
  const [token, setToken] = useState<string>("");
  const [userType, setUserType] = useState<string>("");
  const [user, setUser] = useState<string>("");
  const [dbNames, setDbNames] = useState<string[]>([]);

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
  };

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    const userType = localStorage.getItem("defogUserType");
    const user = localStorage.getItem("defogUser");
    setUser(user);
    setUserType(userType);
    setToken(token);
    getApiKeyNames();
    if (token) setToken(token);
  }, []);

  return (
    token &&
    dbNames.length > 0 && (
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
            initialKeyNames={dbNames}
          />
        </Scaffolding>
      </div>
    )
  );
}
