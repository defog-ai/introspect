import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import { useContext, useEffect, useState } from "react";
import { OracleReportContext } from "$components/context/OracleReportContext";
import { SpinningLoader } from "@defogdotai/agents-ui-components/core-ui";
import setupBaseUrl from "$utils/setupBaseUrl";

function OracleReportImage(props) {
  const { images, keyName, reportId } = useContext(OracleReportContext);

  const { src, alt } = images[props.node.attrs.id] || {};

  const [base64, setBase64] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchImage() {
      try {
        const res = await fetch(
          setupBaseUrl("http", `oracle/get_report_image`),
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Accept: "application/pdf",
              // disable cors for the download
              mode: "no-cors",
            },
            body: JSON.stringify({
              image_file_name: src,
              key_name: keyName,
              report_id: reportId,
            }),
          }
        );

        const data = await res.json();

        if (!data.encoded) {
          throw new Error("Error fetching image");
        }

        const encoded = data.encoded;
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
