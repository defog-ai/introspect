import {
  AnalysisParsed,
  OracleReportContext,
} from "$components/context/OracleReportContext";
import { generateNewAnalysis } from "$utils/oracleUtils";
import { Input } from "@defogdotai/agents-ui-components/core-ui";
import { useContext, useRef, useState } from "react";
import { OracleAnalysis } from "./OracleAnalysis";

export function OracleAnalysisFollowOn({
  initialAnalyses = [],
  recommendationIdx = 0,
}: {
  initialAnalyses: AnalysisParsed[];
  recommendationIdx: number;
}) {
  const [analyses, setAnalyses] = useState(initialAnalyses);

  const [loading, setLoading] = useState<boolean>(false);
  const [loadingAnalysisId, setLoadingAnalysisId] = useState<string | null>(
    null
  );

  const ctr = useRef(null);

  const { reportId, keyName } = useContext(OracleReportContext);

  return (
    <div>
      <div
        className="flex flex-col bg-gray-100 p-4 gap-4 pb-28 dark:bg-gray-600"
        ref={ctr}
      >
        {analyses.map((analysis: AnalysisParsed, i) => {
          return (
            <OracleAnalysis analysis={analysis} key={analysis.analysis_id} />
          );
        })}
        {loading && (
          <OracleAnalysis
            analysis={{
              analysis_id: loadingAnalysisId,
              analysis_json: { analysis_id: loadingAnalysisId },
            }}
            isLoader={true}
          />
        )}
      </div>
      <div className="sticky h-0 bottom-0 overflow-visible">
        <Input
          disabled={loading}
          rootClassNames="bg-gray-50 rounded-lg border border-gray-300 shadow-custom overflow-hidden p-2 h-20 absolute w-10/12 bottom-4 left-0 right-0 mx-auto mb-1"
          inputClassNames="h-9 border-b-2 border-b-gray-300/50"
          onPressEnter={(e) => {
            if (!e.target.value) return;

            const token = localStorage.getItem("defogToken");

            try {
              setLoading(true);
              const analysisId = crypto.randomUUID();

              setLoadingAnalysisId(analysisId);

              generateNewAnalysis(
                reportId,
                analysisId,
                recommendationIdx,
                keyName,
                token,
                e.target.value,
                analyses.map((d) => d.analysis_json)
              )
                .then((d) => {
                  const newAnalysis: AnalysisParsed = {
                    analysis_id: analysisId,
                    mdx: d.mdx,
                    tables: d.tables || {},
                    multiTables: d.multiTables || {},
                    images: d.images || {},
                    analysis_json: d.analysis,
                  };

                  setAnalyses([...analyses, newAnalysis]);

                  setLoading(false);

                  setLoadingAnalysisId(null);
                })
                .catch((e) => {
                  console.error(e);
                  setLoading(false);
                  setLoadingAnalysisId(null);
                });
            } catch (error) {
              console.error(error);
              setLoading(false);
              setLoadingAnalysisId(null);
            }
          }}
          placeholder="Explore further"
        />
        <div className="text-xs text-gray-800/40 absolute bottom-8 w-10/12 left-0 right-0 mx-auto px-3 z-10">
          <span>Type and Press Enter to start a new analysis</span>
        </div>
      </div>
    </div>
  );
}
