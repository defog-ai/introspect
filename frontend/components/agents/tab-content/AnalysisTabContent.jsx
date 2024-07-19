import ErrorBoundary from "$components/layout/ErrorBoundary";
import { DefogAnalysisAgentStandalone } from "../../agents-ui-components/lib/main";

export function AnalysisTabContent({
  selectedDbManager,
  selectedDbKeyName,
  token,
  apiEndpoint,
  predefinedQuestions,
  config = {},
  isTemp = false,
  devMode = false,
}) {
  return (
    <ErrorBoundary>
      <DefogAnalysisAgentStandalone
        analysisVersionManager={selectedDbManager}
        devMode={devMode}
        token={token}
        keyName={selectedDbKeyName}
        apiEndpoint={apiEndpoint}
        autoScroll={true}
        sideBarClasses="h-full"
        searchBarClasses="[&_textarea]:pl-2"
        searchBarDraggable={true}
        predefinedQuestions={predefinedQuestions}
        config={config}
        isTemp={isTemp}
      />
    </ErrorBoundary>
  );
}
