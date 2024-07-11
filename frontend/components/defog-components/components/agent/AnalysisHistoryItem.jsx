import { PlusCircleIcon } from "@heroicons/react/20/solid";
import { twMerge } from "tailwind-merge";

export function AnalysisHistoryItem({
  analysis,
  isActive,
  setActiveAnalysisId,
  setActiveRootAnalysisId,
  setAddToDashboardSelection,
  extraClasses = "",
  isDummy = false,
  onClick = () => {},
}) {
  return (
    <div
      className={twMerge(
        "flex flex-row items-center py-1 px-2 mb-2 hover:cursor-pointer hover:bg-gray-200 history-item",
        isActive ? "font-bold bg-gray-200 " : "",
        isDummy ? "dummy-analysis" : analysis.analysisId,
        extraClasses
      )}
      onClick={() => {
        setActiveRootAnalysisId(analysis?.rootAnalysisId);
        setActiveAnalysisId(analysis?.analysisId);
        onClick();
      }}
    >
      <div className="grow">
        {isDummy ? "New analysis" : analysis?.user_question}
      </div>
      {!isDummy && (
        <div
          className="rounded-sm hover:bg-blue-500 p-1 flex justify-center hover:text-white text-gray-300 group "
          onClick={() => {
            setActiveAnalysisId(analysis?.analysisId);
            // add this to a dashboard
            setAddToDashboardSelection(analysis);
          }}
        >
          <PlusCircleIcon className="w-3 h-3" />
        </div>
      )}
    </div>
  );
}
