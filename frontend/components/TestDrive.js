"use client";
import { DefogAnalysisAgentEmbed } from "@defogdotai/agents-ui-components/agent";

export function TestDrive({ token, dbs, devMode }) {
  return (
    <DefogAnalysisAgentEmbed
      apiEndpoint={process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || ""}
      token={token}
      // these are the ones that will be shown for new csvs uploaded
      uploadedCsvPredefinedQuestions={["Show me any 5 rows from the dataset"]}
      searchBarDraggable={false}
      searchBarClasses="sticky bottom-2"
      dbs={dbs}
      disableMessages={false}
      devMode={devMode}
      // apiEndpoint={"http://localhost:80"}
      // token={
      //   "bdbe4d376e6c8a53a791a86470b924c0715854bd353483523e3ab016eb55bcd0"
      // }
    />
  );
}
