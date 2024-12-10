import { EditorProvider } from "@tiptap/react";
import {
  AnalysisParsed,
  OracleReportContext,
} from "$components/context/OracleReportContext";
import ErrorBoundary from "$components/layout/ErrorBoundary";
import { extensions } from "$utils/oracleUtils";

interface OracleAnalysisProps {
  analysis: AnalysisParsed;
}

export const OracleAnalysis = ({ analysis }: OracleAnalysisProps) => {
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
