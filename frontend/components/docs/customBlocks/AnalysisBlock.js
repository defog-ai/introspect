import { createReactBlockSpec } from "@blocknote/react";
import { createGlobalStyle } from "styled-components";
import { AnalysisAgent } from "../../defog-components/components/agent/AnalysisAgent";
import ErrorBoundary from "../../defog-components/components/common/ErrorBoundary";

function createAnalysisBlockCss(blockId) {
  return createGlobalStyle`div [data-id="${blockId}"] {
  margin: 0.2em 0 !important;
}`;
}

const AnalysisBlock = createReactBlockSpec(
  {
    type: "analysis",
    propSchema: {
      analysisId: {
        default: null,
      },
    },
    content: "none",
  },
  {
    render: ({ block, editor }) => {
      const GlobalStyle = createAnalysisBlockCss(block.id);

      return (
        <ErrorBoundary>
          <GlobalStyle />
          <AnalysisAgent
            analysisId={block.props.analysisId}
            token={editor.token}
            editor={editor}
            block={block}
          />
        </ErrorBoundary>
      );
    },
  }
);

export default AnalysisBlock;
