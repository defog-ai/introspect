"use client";
import {
  BlockNoteView,
  FormattingToolbarPositioner,
  HyperlinkToolbarPositioner,
  SideMenuPositioner,
  SlashMenuPositioner,
  useBlockNote,
} from "@blocknote/react";
import React, { useState, Fragment, useContext, useEffect } from "react";
import { createEditorConfig } from "./createEditorConfig";
import * as Y from "yjs";
import YPartyKitProvider from "y-partykit/provider";
import { CustomFormattingToolbar } from "./CustomFormattingToolbar";
import LoadingReport from "../reports/ReportLoading";
import DocNav from "./DocNav";
import { DocContext, RelatedAnalysesContext } from "./DocContext";
import {
  getAllAnalyses,
  getToolboxes,
  getUserMetadata,
} from "../../utils/utils";
import { DocSidebars } from "./DocSidebars";
import { ReactiveVariablesContext } from "./ReactiveVariablesContext";
import { ReactiveVariableNode } from "./customTiptap/ReactiveVariableNode";
import { ReactiveVariableMention } from "./customTiptap/ReactiveVariableMention";
import { RelatedAnalysesMiniMap } from "../defog-components/components/agent/RelatedAnalysesMiniMap";
import ErrorBoundary from "../common/ErrorBoundary";
import setupBaseUrl from "../../utils/setupBaseUrl";
import { setupWebsocketManager } from "../../utils/websocket-manager";

// remove the last slash from the url
const partyEndpoint = process.env.NEXT_PUBLIC_AGENTS_ENDPOINT;
const recentlyViewedEndpoint = setupBaseUrl(
  "http",
  "add_to_recently_viewed_docs"
);

export function Editor({ docId = null, username = null, apiToken = null }) {
  const [loading, setLoading] = useState(true);
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

  useEffect(() => {
    async function setup() {
      // setup user items
      const items = docContext.userItems;
      const analyses = await getAllAnalyses(apiToken);

      if (analyses && analyses.success) {
        items.analyses = analyses.analyses;
      }
      const toolboxes = await getToolboxes(username);
      if (toolboxes && toolboxes.success) {
        items.toolboxes = toolboxes.toolboxes;
      }

      // also get user's metadata
      const metadata = await getUserMetadata();

      if (metadata && metadata.success) {
        items.metadata = metadata.metadata;
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

      // add to recently viewed docs for this user
      await fetch(recentlyViewedEndpoint, {
        method: "POST",
        body: JSON.stringify({
          api_key: apiToken,
          doc_id: docId,
          username: username,
        }),
      });
    }

    setup();

    return () => {
      if (socketManager && socketManager.close) {
        socketManager.close();
        // also stop the interval
        clearInterval(socketManager.interval);
      }
      if (reRunManager && reRunManager.close) {
        reRunManager.close();
        clearInterval(reRunManager.interval);
      }
      if (toolSocketManager && toolSocketManager.close) {
        toolSocketManager.close();
        clearInterval(toolSocketManager.interval);
      }
    };
  }, []);

  const yjsDoc = new Y.Doc();

  const yjsProvider = new YPartyKitProvider(partyEndpoint, docId, yjsDoc, {
    params: {
      api_token: apiToken,
      doc_id: docId,
      username: username,
    },
    protocol: "ws",
  });

  const editor = useBlockNote({
    ...createEditorConfig(null, yjsDoc, yjsProvider, username),
    _tiptapOptions: {
      extensions: [ReactiveVariableNode, ReactiveVariableMention],
    },
  });

  window.editor = editor;
  editor.apiToken = apiToken;
  editor.username = username;
  window.reactiveContext = reactiveContext;

  editor.onEditorContentChange(() => {
    try {
      // get first text block
      const textBlocks = editor.topLevelBlocks.filter((d) =>
        d?.content?.length ? d?.content[0]?.text : false
      );

      let pageTitle;
      if (!textBlocks?.length || textBlocks[0].content[0].text === "")
        pageTitle = "Untitled document";
      else pageTitle = textBlocks[0].content[0].text;

      // set page title using the first editor block
      document.title = pageTitle;
      yjsDoc.getMap("document-title").set("title", document.title);
    } catch (err) {
      console.log(err);
    }
  });

  yjsProvider.on("sync", () => {
    setLoading(false);
  });

  return !loading ? (
    <RelatedAnalysesContext.Provider
      value={{
        val: relatedAnalysesContext,
        update: setRelatedAnalysesContext,
      }}
    >
      <ReactiveVariablesContext.Provider
        value={{ val: reactiveContext, update: setReactiveContext }}
      >
        <DocContext.Provider value={{ val: docContext, update: setDocContext }}>
          <DocNav
            apiToken={apiToken}
            username={username}
            currentDocId={docId}
          ></DocNav>
          <div id="content">
            <div id="editor-container">
              <BlockNoteView editor={editor} theme={"light"}>
                <FormattingToolbarPositioner
                  editor={editor}
                  formattingToolbar={CustomFormattingToolbar}
                />
                <HyperlinkToolbarPositioner editor={editor} />
                <SlashMenuPositioner editor={editor} />
                <SideMenuPositioner editor={editor} />
              </BlockNoteView>
              <ErrorBoundary>
                <RelatedAnalysesMiniMap editor={editor} />
              </ErrorBoundary>
            </div>
            <DocSidebars />
          </div>
        </DocContext.Provider>
      </ReactiveVariablesContext.Provider>
    </RelatedAnalysesContext.Provider>
  ) : (
    <LoadingReport title={"Loading your document..."} />
  );
}

export default Editor;
