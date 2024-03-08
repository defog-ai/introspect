import { Select, message } from "antd";
import { toolsMetadata } from "../../../../utils/tools_metadata";
import { useEffect, useMemo, useState } from "react";
import { AddStepInputList } from "./AddStepInputList";
import { ToolReRun } from "./ToolReRun";
import setupBaseUrl from "../../../../utils/setupBaseUrl";
import { v4 } from "uuid";

const toolOptions = Object.keys(toolsMetadata).map((tool) => {
  return { value: tool, label: toolsMetadata[tool]?.display_name };
});

const createNewStepEndpoint = setupBaseUrl("http", "create_new_step");

export function AddStepUI({
  analysisId,
  activeNode,
  dag,
  handleReRun = () => {},
  parentNodeData = {},
}) {
  const [selectedTool, setSelectedTool] = useState(
    activeNode?.data?.meta?.tool_name
  );

  // all the default inputs are null, except for pandas dataframes, which are the parent's output
  const sanitizeInputs = (inputs) => {
    // if none of the inputs start with "global_dict.", then add it to the first input that is a string
    if (
      inputs
        .filter((i) => typeof i === "string")
        .filter((i) => i.startsWith("global_dict.")).length === 0
    ) {
      const firstStringInputIdx = inputs.findIndex(
        (i) => typeof i === "string"
      );
      if (firstStringInputIdx !== -1) {
        inputs[firstStringInputIdx] =
          "global_dict." + inputs[firstStringInputIdx];
      }
    }
    return inputs;
  };

  const [inputs, setInputs] = useState(
    sanitizeInputs(activeNode?.data?.meta?.inputs || [])
  );
  const [outputs, setOutputs] = useState(["output_" + v4().split("-")[0]]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setSelectedTool(activeNode?.data?.meta?.tool_name);
    setInputs(sanitizeInputs(activeNode?.data?.meta?.inputs || []));
    setLoading(activeNode?.data?.meta?.loading || false);
  }, [activeNode?.data?.id]);

  return !activeNode ? (
    <>Something went wrong</>
  ) : (
    <div className="add-step-ctr">
      <h1 className="tool-name">New step</h1>
      <h1 className="inputs-header">TOOL</h1>
      <div className="tool-action-buttons">
        <ToolReRun
          text="Run"
          loading={loading || selectedTool === null}
          onClick={async () => {
            setLoading(true);

            try {
              const newStepSuccess = await fetch(createNewStepEndpoint, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({
                  parent_step: activeNode.data.meta.parent_step,
                  tool_name: selectedTool,
                  inputs: inputs,
                  analysis_id: analysisId,
                  outputs_storage_keys: outputs,
                }),
              }).then((r) => r.json());

              activeNode.data.meta.loading = true;

              if (!newStepSuccess.success) {
                message.error(
                  newStepSuccess?.error_message || "Something went wrong"
                );
              } else if (
                !newStepSuccess.new_step ||
                !newStepSuccess.tool_run_id
              ) {
                message.error(
                  "Something went wrong. New step or tool run data or tool run id is missing in the server response."
                );
              } else {
                const toolRunId = newStepSuccess.tool_run_id;

                // re run the tool
                handleReRun(toolRunId, {
                  action: "add_step",
                  new_step: newStepSuccess.new_step,
                });
              }
            } catch (e) {
              console.log(e);
            } finally {
              setLoading(false);
            }
          }}
        />
      </div>
      <Select
        rootClassName="add-step-select-tool-name"
        options={toolOptions}
        value={selectedTool}
        allowClear
        showSearch
        onChange={(value) => {
          if (!activeNode.data.meta.inputs) return;

          activeNode.data.meta.inputs = Array(
            toolsMetadata[value].function_signature.length
          ).fill(null);

          // if there's a pandas dataframe type in the inputs, default that to the parent's output
          toolsMetadata[value].function_signature.forEach((sig, idx) => {
            if (sig.type === "pandas.core.frame.DataFrame") {
              try {
                activeNode.data.meta.inputs[idx] =
                  "global_dict." + activeNode?.data?.parentIds?.[0];
              } catch (e) {
                console.log(e);
              }
            }
          });

          setInputs(activeNode.data.meta.inputs.slice());

          setSelectedTool(value);

          activeNode.data.meta.tool_name = value;
        }}
        placeholder="Select a tool"
      />
      {!selectedTool ? (
        <></>
      ) : (
        <>
          <h1 className="inputs-header">INPUTS</h1>
          <AddStepInputList
            toolRunId={activeNode.data.id}
            toolMetadata={toolsMetadata[selectedTool]}
            analysisId={analysisId}
            inputs={inputs}
            onEdit={(idx, prop, newVal) => {
              activeNode.data.meta.inputs[idx] = newVal;
              setInputs(activeNode.data.meta.inputs.slice());
            }}
            parentNodeData={parentNodeData}
          />
          <h1 className="inputs-header">OUTPUTS</h1>
          {/* a little kooky, but */}
          {/* just reuse AddStepInputList to store outputs */}
          <AddStepInputList
            toolRunId={activeNode.data.id}
            toolMetadata={{
              function_signature: [
                {
                  name: "output_names",
                  default: [],
                  type: "list",
                },
              ],
            }}
            autoFocus={false}
            newListValueDefault={() => "output_" + v4().split("-")[0]}
            inputs={[outputs]}
            onEdit={(idx, prop, newVal) => {
              // don't need to worry about idx, because it's always 0
              setOutputs(newVal);
            }}
            parentNodeData={parentNodeData}
          />
        </>
      )}
    </div>
  );
}
