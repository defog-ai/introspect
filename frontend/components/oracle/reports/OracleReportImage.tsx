import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import { useContext, useEffect, useState } from "react";
import { OracleReportContext } from "$components/context/OracleReportContext";
import { SpinningLoader } from "@defogdotai/agents-ui-components/core-ui";
import { getReportImage } from "$utils/oracleUtils";

function OracleReportImage(props) {
  const { images, keyName, reportId } = useContext(OracleReportContext);

  const { src, alt } = images[props.node.attrs.id] || {};

  const [base64, setBase64] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchImage() {
      try {
        const token = localStorage.getItem("defogToken");
        const encoded = await getReportImage(reportId, keyName, token, src);
        setError(null);

        setBase64("data:image/png;base64," + encoded);
      } catch (e) {
        console.error(e);
        setError("Error fetching image");
      }
    }

    fetchImage();
  }, []);

  return (
    <NodeViewWrapper className="react-component not-prose">
      {error ? (
        <div className="bg-rose-100 text-red text-center rounded-md p-2">
          {error}
        </div>
      ) : base64 ? (
        <img src={base64} alt={alt} />
      ) : (
        <SpinningLoader />
      )}
    </NodeViewWrapper>
  );
}

export const OracleReportImageExtension = Node.create({
  name: "oracle-image",
  group: "block",

  addAttributes() {
    return {
      id: {
        default: null,
      },
    };
  },
  parseHTML() {
    return [
      {
        tag: "oracle-image",
      },
    ];
  },
  renderHTML({ HTMLAttributes }) {
    return ["oracle-image", mergeAttributes(HTMLAttributes)];
  },

  addNodeView() {
    return ReactNodeViewRenderer(OracleReportImage);
  },
});
