import React, {
  useContext,
  useEffect,
  useState,
  Fragment,
  useMemo,
} from "react";
import Context from "./common/Context";
import { v4 } from "uuid";
import { DocContext, RelatedAnalysesContext } from "../../docs/DocContext";
import { ReactiveVariablesContext } from "../../docs/ReactiveVariablesContext";
import { getAllAnalyses, getAllDashboards } from "$utils/utils";
import styled, { createGlobalStyle } from "styled-components";
import ErrorBoundary from "./common/ErrorBoundary";
import setupBaseUrl from "$utils/setupBaseUrl";
import { setupWebsocketManager } from "$utils/websocket-manager";
import AnalysisVersionViewer from "./agent/AnalysisVersionViewer";

export default function DefogAnalysisAgentStandalone({
  analysisId,
  token,
  devMode,
}) {
  const [context, setContext] = useState({});
  const [id, setId] = useState(analysisId || "analysis-" + v4());
  const [docContext, setDocContext] = useState(useContext(DocContext));
  const [reactiveContext, setReactiveContext] = useState(
    useContext(ReactiveVariablesContext)
  );
  const [relatedAnalysesContext, setRelatedAnalysesContext] = useState(
    useContext(RelatedAnalysesContext)
  );

  // this is the main socket manager for the agent
  const [socketManager, setSocketManager] = useState(null);
  // this is for editing tool inputs/outputs
  const [toolSocketManager, setToolSocketManager] = useState(null);
  // this is for handling re runs of tools
  const [reRunManager, setReRunManager] = useState(null);

  const [dashboards, setDashboards] = useState([]);

  useEffect(() => {
    async function setup() {
      // setup user items
      const items = docContext.userItems;
      const analyses = await getAllAnalyses();
      const dashboards = await getAllDashboards(token);
      if (dashboards?.success) {
        setDashboards(dashboards.docs);
      }

      if (analyses && analyses.success) {
        items.analyses = analyses.analyses;
      }

      const urlToConnect = setupBaseUrl("ws", "ws");
      const mgr = await setupWebsocketManager(urlToConnect);
      setSocketManager(mgr);

      const rerunMgr = await setupWebsocketManager(
        urlToConnect.replace("/ws", "/step_rerun")
      );

      setReRunManager(rerunMgr);

      const toolSocketManager = await setupWebsocketManager(
        urlToConnect.replace("/ws", "/edit_tool_run"),
        (d) => console.log(d)
      );
      setToolSocketManager(toolSocketManager);

      setDocContext({
        ...docContext,
        userItems: items,
        socketManagers: {
          mainManager: mgr,
          reRunManager: rerunMgr,
          toolSocketManager: toolSocketManager,
        },
      });
    }

    setup();

    return () => {
      if (socketManager && socketManager.close) {
        socketManager.close();
        // also stop the timeout
        socketManager.clearSocketTimeout();
      }
      if (reRunManager && reRunManager.close) {
        reRunManager.close();
        reRunManager.clearSocketTimeout();
      }
      if (toolSocketManager && toolSocketManager.close) {
        toolSocketManager.close();
        toolSocketManager.clearSocketTimeout();
      }
    };
  }, []);

  const GlobalStyle = createGlobalStyle``;

  return (
    <ErrorBoundary>
      <RelatedAnalysesContext.Provider
        value={{
          val: relatedAnalysesContext,
          update: setRelatedAnalysesContext,
        }}
      >
        <ReactiveVariablesContext.Provider
          value={{ val: reactiveContext, update: setReactiveContext }}
        >
          <DocContext.Provider
            value={{ val: docContext, update: setDocContext }}
          >
            <Context.Provider value={[context, setContext]}>
              <GlobalStyle />
              <FontLoadCss>
                <div className="content md:w-11/12">
                  <div className="editor-container mt-4 mb-8">
                    <div className="defog-analysis-container">
                      <div
                        data-content-type="analysis"
                        data-analysis-id={analysisId}
                      >
                        <AnalysisVersionViewer
                          token={token}
                          dashboards={dashboards}
                          devMode={devMode}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </FontLoadCss>
            </Context.Provider>
          </DocContext.Provider>
        </ReactiveVariablesContext.Provider>
      </RelatedAnalysesContext.Provider>
    </ErrorBoundary>
  );
}

// font loader
const FontLoadCss = styled.div`
  @import url("https://fonts.googleapis.com/css2?family=Inter:wght@100..900");
  @import url("https://fonts.googleapis.com/css2?family=Fira+Code:wght@300..700&display=swap");
`;
