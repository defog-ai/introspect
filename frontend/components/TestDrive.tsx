"use client";
import { QueryDataEmbed } from "@defogdotai/agents-ui-components/agent";
import { SpinningLoader } from "@defogdotai/agents-ui-components/core-ui";
import React, { useRef } from "react";
import { useCallback, useEffect, useState } from "react";

export function TestDrive({
  token,
  dbs,
  hideSqlTab = false,
  hidePreviewTabs = false,
  hiddenCharts = [],
  hideRawAnalysis = false,
}: {
  token: string;
  dbs: {
    name: string;
    predefinedQuestions: string[];
  }[];
  hideSqlTab?: boolean;
  hidePreviewTabs?: boolean;
  hiddenCharts?: string[];
  hideRawAnalysis?: boolean;
}) {
  const [initialTrees, setInitialTrees] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}/get_user_history`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ token }),
    })
      .then((res) => {
        if (!res.ok) {
          return { error: "Could not fetch user history" };
        }
        return res.json();
      })
      .then((data) => {
        if (data.error) {
          setError(data.error);
          return;
        }
        setLoading(false);
        setInitialTrees(data.history || {});
      });
  }, []);

  const updateUserHistory = useCallback((dbName, history) => {
    if (!dbName || !history) return;
    try {
      fetch(
        `${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}/update_user_history`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ token, history, db_name: dbName }),
        }
      )
        .then((res) => res.json())
        .then((data) => {
          if (data.error) throw Error(data.error);
        });
    } catch (err) {
      console.error(err);
    }
  }, []);

  return !loading && !error && initialTrees ? (
    <QueryDataEmbed
      initialDbList={dbs}
      hiddenCharts={["boxplot", "histogram"]}
      token={token}
      searchBarDraggable={false}
      hidePreviewTabs={false}
      apiEndpoint={process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}
      initialTrees={initialTrees}
      hideRawAnalysis={hideRawAnalysis}
      hideSqlTab={hideSqlTab}
      onTreeChange={(dbName, tree) => {
        updateUserHistory(dbName, tree);
      }}
    />
  ) : (
    <div className="w-full h-full flex items-center justify-center text-gray-400">
      {error ? (
        `${error}`
      ) : (
        <>
          <SpinningLoader /> Loading
        </>
      )}
    </div>
  );
}
