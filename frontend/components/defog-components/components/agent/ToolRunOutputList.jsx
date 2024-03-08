import { CaretDownOutlined, CaretRightOutlined } from "@ant-design/icons";
import { CodeEditor } from "../CodeEditor";
import { useRef, useState } from "react";

export function ToolRunOutputList({
  analysisId,
  toolRunId,
  step,
  sql = null,
  codeStr = null,
  handleEdit = () => {},
  availableOutputNodes = [],
  setActiveNode,
}) {
  //   parse outputs
  //   each output is a node somewhere in the dag

  const codeCtrRef = useRef(null);
  const [codeCollapsed, setCodeCollapsed] = useState(true);

  return (
    <div className="tool-output-list">
      <div className="tool-code">
        {sql && (
          <>
            <p className="tool-code-header">SQL</p>
            <CodeEditor
              key={sql}
              className="tool-code-ctr"
              analysisId={analysisId}
              toolRunId={toolRunId}
              code={sql}
              handleEdit={handleEdit}
              updateProp={"sql"}
            ></CodeEditor>
          </>
        )}
        {codeStr && (
          <>
            <p
              style={{ pointerEvents: "all", cursor: "pointer" }}
              className="tool-code-header"
              onClick={() => {
                setCodeCollapsed(!codeCollapsed);
                // get scroll height of tool-code-ctr inside codeCtrRef
                if (codeCtrRef.current) {
                  const codeCtr =
                    codeCtrRef.current.querySelector(".tool-code-ctr");
                  if (codeCtr) {
                    codeCtrRef.current.style.maxHeight = codeCollapsed
                      ? `${codeCtr.scrollHeight}px`
                      : "0px";
                  }
                }
              }}
            >
              <span>
                {
                  <CaretRightOutlined
                    style={{
                      transition: "transform 0.3s ease-in-out",
                      marginRight: "3px",
                      top: "1px",
                      transform: codeCollapsed
                        ? "rotate(0deg)"
                        : "rotate(90deg)",
                    }}
                  />
                }
              </span>
              Code
            </p>
            <div
              ref={codeCtrRef}
              style={{
                overflow: "hidden",
                maxHeight: "0px",
                transition: "max-height 0.6s ease-in-out",
              }}
            >
              <CodeEditor
                key={codeStr}
                className="tool-code-ctr"
                analysisId={analysisId}
                toolRunId={toolRunId}
                code={codeStr}
                language="python"
                handleEdit={handleEdit}
                updateProp={"code_str"}
              ></CodeEditor>
            </div>
          </>
        )}
      </div>
      <div className="tool-output-data">
        <p className="tool-output-data-header">Datasets</p>
        {step.outputs_storage_keys.map((output, i) => {
          return (
            <div
              key={i}
              className="tool-output-data-value"
              onClick={() => {
                const exists = availableOutputNodes.find(
                  (node) => node.data.id === output
                );
                if (exists) {
                  setActiveNode(exists);
                }
              }}
              onMouseOver={(ev) => {
                // get the closest .analysis-content to the mouseovered element
                const closest = ev.target.closest(".analysis-content");
                if (!closest) return;
                // now get the closest .graph-node with the class name output
                const node = closest.querySelector(`.graph-node.${output}`);
                if (!node) return;
                // add a class highlighted
                node.classList.add("highlighted");
              }}
              onMouseOut={(ev) => {
                // get the closest .analysis-content to the mouseovered element
                const closest = ev.target.closest(".analysis-content");
                if (!closest) return;
                // now get the closest .graph-node with the class name output
                const node = closest.querySelector(`.graph-node.${output}`);
                if (!node) return;
                // remove the class highlighted
                node.classList.remove("highlighted");
              }}
            >
              <span>{output}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
