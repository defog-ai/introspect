import { EditorProvider } from "@tiptap/react";
import {
  AnalysisParsed,
  OracleReportContext,
} from "$components/context/OracleReportContext";
import ErrorBoundary from "$components/layout/ErrorBoundary";
import { extensions, getAnalysisStatus } from "$utils/oracleUtils";
import { useContext, useEffect, useState } from "react";
import { SpinningLoader } from "@defogdotai/agents-ui-components/core-ui";
import { toSentenceCase } from "$utils/utils";

interface OracleAnalysisProps {
  analysis: AnalysisParsed;
  isLoader?: boolean;
}

export const OracleAnalysis = ({
  analysis,
  isLoader = false,
}: OracleAnalysisProps) => {
  const [analysisStatus, setAnalysisStatus] = useState<string>("Loading");
  const { reportId, keyName } = useContext(OracleReportContext);

  useEffect(() => {
    let timeout;

    async function getStatus() {
      const token = localStorage.getItem("defogToken");
      try {
        const status = await getAnalysisStatus(
          reportId,
          analysis.analysis_id,
          keyName,
          token
        );

        setAnalysisStatus(toSentenceCase(status));
      } catch (e) {
        console.error(e);
      } finally {
        if (analysisStatus !== "done") {
          clearTimeout(timeout);
          timeout = setTimeout(getStatus, 1000);
        }
      }
    }

    if (isLoader && analysis.analysis_id) {
      getStatus();
    }

    return () => clearTimeout(timeout);
  });

  if (isLoader) {
    return (
      <div className="rounded-lg border drop-shadow-md text-center text-gray-500 bg-white p-4 min-h-20">
        <SpinningLoader classNames="m-0 mb-2" />
        <p> {analysisStatus || "Exploring..."}</p>
      </div>
    );
  }

  if (!analysis.mdx) {
    return (
      <div className="text-red-500 p-4 rounded-lg border border-red-200 bg-red-50">
        No analysis content available
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="rounded-lg border drop-shadow-md bg-white py-4">
        <OracleReportContext.Provider
          value={{
            tables: analysis.tables,
            multiTables: analysis.multiTables,
            images: analysis.images,
          }}
        >
          <EditorProvider
            extensions={extensions}
            content={analysis.mdx}
            editable={false}
            editorProps={{
              attributes: {
                class:
                  "oracle-report-tiptap prose prose-base mx-auto p-2 mb-12 md:mb-0 focus:outline-none [&_.react-multitable-container]:lg:mx-0",
              },
            }}
          />
        </OracleReportContext.Provider>
      </div>
    </ErrorBoundary>
  );
};
