import { Select, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { AddStepInputList } from "./AddStepInputList";
import { ToolReRun } from "./ToolReRun";
import setupBaseUrl from "$utils/setupBaseUrl";
import { v4 } from "uuid";
import { createInitialToolInputs } from "$utils/utils";

const createNewStepEndpoint = setupBaseUrl("http", "create_new_step");

export function AddStepUI({
  analysisId,
  activeNode,
  dag,
  handleReRun = () => {},
  parentNodeData = {},
  tools = {},
}) {
  const toolOptions = Object.keys(tools).map((tool) => {
    return { value: tool, label: tools[tool]?.tool_name };
  });

  const [selectedTool, setSelectedTool] = useState(
    activeNode?.data?.step?.tool_name
  );

  // all the default inputs are null, except for pandas dataframes, which are the parent's output
  const sanitizeInputs = (inputs) => {
    return inputs;
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
    sanitizeInputs(activeNode?.data?.step?.inputs || {})
  );
  const [outputs, setOutputs] = useState(["output_" + v4().split("-")[0]]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setSelectedTool(activeNode?.data?.step?.tool_name);
    setInputs(sanitizeInputs(activeNode?.data?.step?.inputs || {}));
    setLoading(activeNode?.data?.step?.loading || false);
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
            console.groupCollapsed("AddStepUI: Run button clicked");
            console.log("inputs", inputs);
            console.log("outputs", outputs);
            console.groupEnd();

            try {
              const newStepSuccess = await fetch(createNewStepEndpoint, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({
                  parent_step: activeNode.data?.step?.parent_step,
                  tool_name: selectedTool,
                  inputs: inputs,
                  analysis_id: analysisId,
                  outputs_storage_keys: outputs,
                }),
              }).then((r) => r.json());

              activeNode.data.step.loading = true;

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
          if (!activeNode.data?.step?.inputs) return;
          const initialInputs = createInitialToolInputs(
            value,
            activeNode?.data?.parentIds
          );

          setInputs(initialInputs);

          setSelectedTool(value);

          activeNode.data.step.tool_name = value;
          activeNode.data.step.inputs = initialInputs;
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
            toolMetadata={tools[selectedTool]}
            analysisId={analysisId}
            inputs={inputs}
            onEdit={(prop, newVal) => {
              activeNode.data.step.inputs[prop] = newVal;
              setInputs(Object.assign({}, activeNode.data?.step?.inputs));
            }}
            parentNodeData={parentNodeData}
          />
          <h1 className="inputs-header">OUTPUTS</h1>
          {/* a little kooky, but */}
          {/* just reuse AddStepInputList to store outputs */}
          <AddStepInputList
            toolRunId={activeNode.data.id}
            toolMetadata={{
              input_metadata: [
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
            onEdit={(prop, newVal) => {
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
