"use client";
import { DefogAnalysisAgentEmbed } from "@defogdotai/agents-ui-components/agent";
import { SpinningLoader } from "@defogdotai/agents-ui-components/core-ui";
import { useCallback, useEffect, useState } from "react";

export function TestDrive({
  token,
  dbs,
  devMode,
  isAdmin = false,
  hideSqlTab = false,
  hidePreviewTabs = false,
  hiddenCharts = [],
  hideRawAnalysis = false,
}) {
  const [initialTrees, setInitialTrees] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // const initialTrees = useMemo(() => {
  //   try {
  //     const storedTrees = localStorage.getItem("analysisTrees");
  //     if (storedTrees) {
  //       return JSON.parse(storedTrees);
  //     }
  //   } catch (e) {
  //     return null;
  //   }
  // }, []);

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

  const updateUserHistory = useCallback((keyName, history) => {
    try {
      fetch(
        `${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}/update_user_history`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ token, history, key_name: keyName }),
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
    <DefogAnalysisAgentEmbed
      apiEndpoint={process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}
      token={token}
      isAdmin={isAdmin}
      hideSqlTab={hideSqlTab}
      hidePreviewTabs={hidePreviewTabs}
      hiddenCharts={hiddenCharts}
      hideRawAnalysis={hideRawAnalysis}
      // these are the ones that will be shown for new csvs uploaded
      uploadedCsvPredefinedQuestions={["Show me any 5 rows from the dataset"]}
      searchBarDraggable={false}
      dbs={dbs}
      disableMessages={false}
      devMode={devMode}
      initialTrees={initialTrees}
      onTreeChange={(keyName, tree) => {
        try {
          // // save in local storage in an object called analysisTrees
          // let trees = localStorage.getItem("analysisTrees");
          // if (!trees) {
          //   trees = {};
          //   localStorage.setItem("analysisTrees", "{}");
          // } else {
          //   trees = JSON.parse(trees);
          // }

          // trees[keyName] = tree;
          // localStorage.setItem("analysisTrees", JSON.stringify(trees));
          updateUserHistory(keyName, tree);
        } catch (e) {
          console.error(e);
        }
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
