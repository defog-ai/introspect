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

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    const userType = localStorage.getItem("defogUserType");
    const user = localStorage.getItem("defogUser");
    setUser(user);
    setUserType(userType);
    setToken(token);
    if (token) setToken(token);
  }, []);

  return (
    token &&
    userType &&
    user && (
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
          />
        </Scaffolding>
      </div>
    )
  );
}
