"use client";
import { useEffect, useState } from "react";
import { OracleEmbed } from "@defogdotai/agents-ui-components/oracle";

// Main Component
export default function OracleDashboard() {
  const [token, setToken] = useState<string>(null);

  const updateToken = useEffect(() => {
    const token = localStorage.getItem("defogToken");
    if (token) setToken(token);
  }, []);

  return (
    token && (
      <OracleEmbed
        apiEndpoint={process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}
        token={token}
      />
    )
  );
}
