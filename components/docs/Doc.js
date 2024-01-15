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
import { getAllAnalyses, getToolboxes } from "../../utils/utils";
import { DocSidebars } from "./DocSidebars";
import { ReactiveVariablesContext } from "./ReactiveVariablesContext";
import { ReactiveVariableNode } from "./customTiptap/ReactiveVariableNode";
import { ReactiveVariableMention } from "./customTiptap/ReactiveVariableMention";
import { RelatedAnalysesMiniMap } from "../defog-components/components/agent/RelatedAnalysesMiniMap";
import ErrorBoundary from "../common/ErrorBoundary";

// remove the last slash from the url
const partyEndpoint = process.env.NEXT_PUBLIC_PARTYKIT_ENDPOINT;

export function Editor({ docId = null, username = null, apiToken = null }) {
  const [loading, setLoading] = useState(true);
  const [docContext, setDocContext] = useState(useContext(DocContext));

  const [reactiveContext, setReactiveContext] = useState(
    useContext(ReactiveVariablesContext)
  );

  const [relatedAnalysesContext, setRelatedAnalysesContext] = useState(
    useContext(RelatedAnalysesContext)
  );

  useEffect(() => {
    async function getUserItems() {
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

      setDocContext({
        ...docContext,
        userItems: items,
      });
    }
    getUserItems();
  }, []);

  const yjsDoc = new Y.Doc();

  const yjsProvider = new YPartyKitProvider(partyEndpoint, docId, yjsDoc, {
    params: {
      api_token: apiToken,
      doc_id: docId,
      username: username,
    },
  });

  const editor = useBlockNote({
    ...createEditorConfig(null, yjsDoc, yjsProvider, username),
    _tiptapOptions: {
      extensions: [ReactiveVariableNode, ReactiveVariableMention],
    },
  });

  window.editor = editor;
  editor.apiToken = apiToken;
  window.reactiveContext = reactiveContext;

  editor.onEditorContentChange(() => {
    try {
      // only if a change
      if (document.title === editor?.topLevelBlocks[0]?.content[0]?.text)
        return;

      // set page title using the first editor block
      document.title =
        editor?.topLevelBlocks[0]?.content[0]?.text || "Untitled document";
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
          <DocNav apiToken={apiToken} currentDocId={docId}></DocNav>
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
