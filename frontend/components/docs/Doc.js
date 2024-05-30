"use client";
import {
  BlockNoteView,
  FormattingToolbarController,
  SuggestionMenuController,
  useCreateBlockNote,
} from "@blocknote/react";
import React, { useState, Fragment, useContext, useEffect } from "react";
import { createEditorConfig } from "./createEditorConfig";
import * as Y from "yjs";
import YPartyKitProvider from "y-partykit/provider";
import { CustomFormattingToolbar } from "./CustomFormattingToolbar";
import LoadingReport from "../reports/ReportLoading";
import DocNav from "./DocNav";
import { DocContext, RelatedAnalysesContext } from "./DocContext";
import { getAllAnalyses, getToolboxes, getUserMetadata } from "$utils/utils";
import { DocSidebars } from "./DocSidebars";
import { ReactiveVariablesContext } from "./ReactiveVariablesContext";
import { ReactiveVariableNode } from "./customTiptap/ReactiveVariableNode";
import { ReactiveVariableMention } from "./customTiptap/ReactiveVariableMention";
import setupBaseUrl from "$utils/setupBaseUrl";
import { setupWebsocketManager } from "$utils/websocket-manager";
import { customBlockSchema } from "./createCustomBlockSchema";
import { filterSuggestionItems } from "@blocknote/core";
import { getCustomSlashMenuItems } from "./createCustomSlashMenuItems";

// remove the last slash from the url
const partyEndpoint = process.env.NEXT_PUBLIC_AGENTS_ENDPOINT;
const recentlyViewedEndpoint = setupBaseUrl(
  "http",
  "add_to_recently_viewed_docs"
);

export function Editor({ docId = null, username = null }) {
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
      const analyses = await getAllAnalyses();

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
          doc_id: docId,
          username: username,
        }),
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

  const yjsDoc = new Y.Doc();

  const yjsProvider = new YPartyKitProvider(partyEndpoint, docId, yjsDoc, {
    params: {
      doc_id: docId,
      username: username,
    },
    protocol: "ws",
  });

  const editor = useCreateBlockNote({
    ...createEditorConfig(null, yjsDoc, yjsProvider, username),
    placeholders: {
      default: "Type /analysis to start",
    },
    schema: customBlockSchema,
    _tiptapOptions: {
      extensions: [ReactiveVariableNode, ReactiveVariableMention],
    },
  });

  window.editor = editor;
  editor.username = username;
  window.reactiveContext = reactiveContext;

  editor.onEditorContentChange(() => {
    try {
      // get first text block
      const textBlocks = editor.document.filter((d) =>
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
          <DocNav username={username} currentDocId={docId}></DocNav>
          <div className="content">
            <div className="editor-container">
              <BlockNoteView
                editor={editor}
                theme={"light"}
                formattingToolbar={false}
                slashMenu={false}
              >
                <FormattingToolbarController
                  editor={editor}
                  formattingToolbar={CustomFormattingToolbar}
                />
                <SuggestionMenuController
                  editor={editor}
                  triggerCharacter="/"
                  getItems={async (query) =>
                    filterSuggestionItems(
                      getCustomSlashMenuItems(editor),
                      query
                    )
                  }
                />
              </BlockNoteView>
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
