"use client";
import { useEffect, useState } from "react";
import { OracleEmbed } from "@defogdotai/agents-ui-components/oracle";
import Scaffolding from "$components/layout/Scaffolding";
import Meta from "$components/layout/Meta";
import { SpinningLoader } from "@defogdotai/agents-ui-components/core-ui";
import { useRouter } from "next/router";

// Main Component
export default function OracleDashboard() {
  const router = useRouter();
  const [token, setToken] = useState<string>("");
  const [userType, setUserType] = useState<string>("");
  const [dbNames, setDbNames] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const getApiKeyNames = async () => {
    const token =
      localStorage.getItem("defogToken") ||
      "4adaf64ff68cd84fb8f3aa6366812cb8aa20a8cd8d1abd156d15d578bea6680a";
    if (!token) {
      setLoading(false);
      return;
    }

    try {
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
    } catch (error) {
      console.error("Error fetching db names:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const token =
      localStorage.getItem("defogToken") ||
      "4adaf64ff68cd84fb8f3aa6366812cb8aa20a8cd8d1abd156d15d578bea6680a";
    const userType = localStorage.getItem("defogUserType");

    if (!token) {
      // Redirect to login page after a short delay
      setTimeout(() => {
        // Capture current URL with all query parameters
        const returnUrl = window.location.pathname + window.location.search;

        router.push({
          pathname: "/log-in",
          query: {
            message: "You are not logged in. Please log in to access reports.",
            returnUrl,
          },
        });
      }, 1500);
    } else {
      setUserType(userType);
      setToken(token);
      getApiKeyNames();
    }
  }, [router]);

  if (!token && !loading) {
    return (
      <div className="h-screen flex flex-col items-center justify-center">
        <Meta />
        <div className="text-center p-6">
          <h2 className="text-xl font-semibold mb-2">Not Logged In</h2>
          <p className="mb-4">
            You are not logged in. Redirecting to login page...
          </p>
          <SpinningLoader />
        </div>
      </div>
    );
  }

  return loading === true ? (
    <SpinningLoader />
  ) : (
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
          initialProjectNames={dbNames}
        />
      </Scaffolding>
    </div>
  );
}
