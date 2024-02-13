import { Input, Select } from "antd";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { MdDeleteOutline, MdOutlineAddBox } from "react-icons/md";

const inputTypeToUI = {
  list: (toolRunId, inputName, initialValue, onEdit) => {
    if (!initialValue) initialValue = [];
    return (
      <span className="tool-input-value tool-input-type-list">
        <span className="list-bracket">[</span>
        {initialValue.map((val, i) => {
          return (
            <span key={toolRunId + "_" + inputName}>
              <Input
                value={val}
                size="small"
                suffix={
                  <MdDeleteOutline
                    onClick={() =>
                      onEdit(
                        inputName,
                        initialValue.filter((v, j) => j !== i)
                      )
                    }
                  />
                }
                onChange={(ev) => {
                  // replace the value at i with the new value
                  const newVal = initialValue.map((v, j) => {
                    if (i === j) {
                      return ev.target.value;
                    }
                    return v;
                  });
                  onEdit(inputName, newVal);
                }}
              />
              {i !== initialValue.length - 1 ? (
                <span className="list-separator">, </span>
              ) : (
                <></>
              )}
            </span>
          );
        })}
        <div className="list-add">
          <MdOutlineAddBox
            onClick={() => {
              onEdit(inputName, [...initialValue, "New Value"]);
            }}
          ></MdOutlineAddBox>
        </div>
        <span className="list-bracket">]</span>
      </span>
    );
  },
  str: (toolRunId, inputName, initialValue, onEdit) => {
    if (!initialValue) initialValue = "";
    return (
      <Input
        rootClassName="tool-input-value"
        value={initialValue}
        key={toolRunId + "_" + inputName}
        size="small"
        onChange={(ev) => {
          onEdit(inputName, ev.target.value);
        }}
      />
    );
  },
  bool: (toolRunId, inputName, initialValue, onEdit) => {
    if (!initialValue) initialValue = false;
    return (
      <Select
        rootClassName="tool-input-value"
        value={String(initialValue)}
        key={toolRunId + "_" + inputName}
        size="small"
        popupClassName="tool-input-value-dropdown"
        options={[
          { label: "true", value: true },
          { label: "false", value: false },
        ]}
        onChange={(val) => {
          onEdit(inputName, val);
        }}
      />
    );
  },
  int: (toolRunId, inputName, initialValue, onEdit) => {
    if (!initialValue) initialValue = 0;

    return (
      <Input
        rootClassName="tool-input-value"
        key={toolRunId + "_" + inputName}
        value={initialValue}
        type="number"
        size="small"
        onChange={(ev) => {
          onEdit(inputName, parseFloat(ev.target.value));
        }}
      />
    );
  },
  float: (toolRunId, inputName, initialValue, onEdit) => {
    if (!initialValue) initialValue = 0.0;
    return (
      <Input
        value={initialValue}
        key={toolRunId + "_" + inputName}
        size="small"
        type="number"
        onChange={(ev) => {
          onEdit(inputName, parseFloat(ev.target.value));
        }}
      />
    );
  },
  "pandas.core.frame.DataFrame": (
    toolRunId,
    inputName,
    initialValue,
    onEdit,
    availableOutputNodes = [],
    setActiveNode = () => {}
  ) => {
    if (!initialValue) initialValue = "";
    const name_clipped = initialValue?.replace(/global_dict\./g, "");
    const exists = availableOutputNodes.find(
      (node) => node.data.id === name_clipped
    );

    return (
      <span
        className="tool-input-value type-df"
        onClick={() => {
          if (exists) {
            setActiveNode(exists);
          }
        }}
        onMouseOver={(ev) => {
          // get the closest .analysis-content to the mouseovered element
          const closest = ev.target.closest(".analysis-content");
          if (!closest) return;
          // now get the closest .graph-node with the class name output
          const node = closest.querySelector(`.graph-node.${name_clipped}`);
          if (!node) return;
          // add a class highlighted
          node.classList.add("highlighted");
        }}
        onMouseOut={(ev) => {
          // get the closest .analysis-content to the mouseovered element
          const closest = ev.target.closest(".analysis-content");
          if (!closest) return;
          // now get the closest .graph-node with the class name name_clipped
          const node = closest.querySelector(`.graph-node.${name_clipped}`);
          if (!node) return;
          // remove the class highlighted
          node.classList.remove("highlighted");
        }}
      >
        {name_clipped}
      </span>
    );
  },
};

export function ToolRunInputList({
  analysisId,
  toolRunId,
  step,
  availableOutputNodes = [],
  setActiveNode = () => {},
  handleEdit = () => {},
  autoFocus = true,
}) {
  //   parse inputs
  // if inputs doesn't start with global_dict, then it's it's type is whatever typeof returns
  // if it does start with global_dict, then it is a pandas dataframe
  // with a corresponding node somewhere in the dag

  const [inputs, setInputs] = useState(step.inputs);
  const [functionSignature, setFunctionSignature] = useState(
    step.function_signature
  );

  const ctr = useRef(null);

  // index is index in the step["inputs"] array
  function onEdit(index, prop, newVal) {
    const newInputs = [...inputs];
    newInputs[index] = newVal;
    setInputs(newInputs);
    handleEdit({
      analysis_id: analysisId,
      tool_run_id: toolRunId,
      update_prop: "inputs",
      new_val: newInputs,
    });
  }

  useEffect(() => {
    setInputs(step.inputs);
    setFunctionSignature(step.function_signature);
  }, [step]);

  return (
    <div className="tool-input-list" key={toolRunId} ref={ctr}>
      {inputs.map((input, i) => {
        return (
          <div key={i + "_" + toolRunId} className="tool-input">
            <span className="tool-input-type">{functionSignature[i].type}</span>
            <span className="tool-input-name">{functionSignature[i].name}</span>

            {inputTypeToUI[functionSignature[i].type] ? (
              inputTypeToUI[functionSignature[i].type](
                toolRunId,
                functionSignature[i].name,
                input,
                function (prop, newVal) {
                  onEdit(i, prop, newVal);
                },
                availableOutputNodes,
                setActiveNode
              )
            ) : (
              <span className="tool-input-value" contentEditable>
                {step.inputs.length - 1 < i
                  ? String(functionSignature[i].default)
                  : String(input)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
