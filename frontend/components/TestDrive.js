"use client";
import { DefogAnalysisAgentEmbed } from "@defogdotai/agents-ui-components/agent";
import { useEffect, useState } from "react";

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
    fetch(`${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/get_user_history`, {
      method: "POST",
      body: JSON.stringify({ token }),
    })
      .then((res) => res.json())
      .then((data) => setInitialTrees(data.history));
  }, []);

  const updateUserHistory = (history) => {
    fetch(`${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/update_user_history`, {
      method: "POST",
      body: JSON.stringify({ token, history }),
    });
  };

  return (
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
          // save in local storage in an object called analysisTrees
          let trees = localStorage.getItem("analysisTrees");
          if (!trees) {
            trees = {};
            localStorage.setItem("analysisTrees", "{}");
          } else {
            trees = JSON.parse(trees);
          }

          trees[keyName] = tree;
          localStorage.setItem("analysisTrees", JSON.stringify(trees));
          updateUserHistory(trees);
        } catch (e) {
          console.error(e);
        }
      }}
    />
  );
}
