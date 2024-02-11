import { Input, Select } from "antd";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { MdDeleteOutline, MdOutlineAddBox } from "react-icons/md";

const onHover = (ev, label, analysisId) => {
  // get the closest .analysis-content to the mouseovered element
  const closest = document.querySelector(
    `div[data-analysis-id="${analysisId}"]`
  );
  if (!closest) return;
  // now get the closest .graph-node with the class name output
  const node = closest.querySelector(`.graph-node.${label}`);
  if (!node) return;
  // add a class highlighted
  node.classList.add("highlighted");
};
const onHoverOut = (ev, label, analysisId) => {
  // get the closest .analysis-content to the mouseovered element
  const closest = document.querySelector(
    `div[data-analysis-id="${analysisId}"]`
  );
  if (!closest) return;
  // now get the closest .graph-node with the class name output
  const node = closest.querySelector(`.graph-node.${label}`);
  if (!node) return;
  // remove the class highlighted
  node.classList.remove("highlighted");
};

const inputTypeToUI = {
  list: (
    inputName,
    initialValue,
    onEdit,
    config = { newListValueDefault: "New Value" }
  ) => {
    if (!initialValue || !Array.isArray(initialValue)) initialValue = [];

    return (
      <span className="tool-input-value tool-input-type-list">
        <span className="list-bracket">[</span>
        {initialValue.map((val, i) => {
          return (
            <span key={inputName}>
              <Input
                // autoFocus={config?.autoFocus}
                defaultValue={val}
                size="small"
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
        <span className="list-bracket">]</span>
      </span>
    );
  },
  str: (inputName, initialValue, onEdit, config = {}) => {
    if (!initialValue) initialValue = "";
    return (
      <Input
        autoFocus={config?.autoFocus}
        rootClassName="tool-input-value"
        defaultValue={initialValue || ""}
        size="small"
        onChange={(ev) => {
          onEdit(inputName, ev.target.value);
        }}
      />
    );
  },
  bool: (inputName, initialValue, onEdit, config = {}) => {
    return (
      <Select
        autoFocus={config?.autoFocus}
        rootClassName="tool-input-value"
        placeholder="Select a value"
        defaultValue={initialValue || null}
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
  int: (inputName, initialValue, onEdit, config = {}) => (
    <Input
      autoFocus={config?.autoFocus}
      rootClassName="tool-input-value"
      defaultValue={initialValue || ""}
      type="number"
      size="small"
      onChange={(ev) => {
        onEdit(inputName, parseFloat(ev.target.value));
      }}
    />
  ),
  float: (inputName, initialValue, onEdit, config = {}) => (
    <Input
      autoFocus={config?.autoFocus}
      size="small"
      type="number"
      defaultValue={initialValue}
      onChange={(ev) => {
        onEdit(inputName, parseFloat(ev.target.value));
      }}
    />
  ),
  "pandas.core.frame.DataFrame": (
    inputName,
    initialValue,
    onEdit,
    config = { availableInputDfs: [], analysisId: "", autoFocus: false }
  ) => {
    const options =
      config?.availableInputDfs?.map((df) => {
        return { label: df.data.id, value: "global_dict." + df.data.id };
      }) || [];

    // return <span className="tool-input-value type-df">{name_clipped}</span>;

    return (
      <Select
        showSearch
        placeholder="Select a value"
        rootClassName="add-step-df-select-ctr"
        onChange={(val) => {
          onEdit(inputName, val);
        }}
        defaultValue={initialValue}
        optionRender={(option) => {
          return (
            <div
              className="tool-input-data-value"
              onMouseOver={(ev) => onHover(ev, option.label, config.analysisId)}
              onMouseOut={(ev) =>
                onHoverOut(ev, option.label, config.analysisId)
              }
            >
              <span>{option?.label}</span>
            </div>
          );
        }}
        tagRender={(option) => {
          return (
            <div
              className="tool-input-data-value"
              onMouseOver={(ev) => onHover(ev, option.label, config.analysisId)}
              onMouseOut={(ev) =>
                onHoverOut(ev, option.label, config.analysisId)
              }
            >
              <span>{option?.label}</span>
            </div>
          );
        }}
        size="small"
        popupClassName="add-step-df-dropdown"
        options={options}
      />
    );
  },
};

export function AddStepInputList({
  toolRunId,
  analysisId,
  toolMetadata,
  availableInputDfs = [],
  inputs = [],
  onEdit = () => {},
  newListValueDefault = "New Value",
  autoFocus = true,
}) {
  const functionSignature = toolMetadata?.function_signature || [];
  const ctr = useRef(null);

  // useEffect(() => {
  //   // if autoFocus, focus onthe first input
  //   if (ctr && autoFocus) {
  //     ctr?.current?.querySelector("input[type=text]")?.focus();
  //   }
  // });

  return (
    <div className="tool-input-list" key={toolRunId} ref={ctr}>
      {inputs.map((input, i) => {
        return (
          <div key={i + "_" + toolRunId} className="tool-input">
            <span className="tool-input-type">{functionSignature[i].type}</span>
            <span className="tool-input-name">{functionSignature[i].name}</span>
            {inputTypeToUI[functionSignature[i].type](
              functionSignature[i].name,
              input,
              function (prop, newVal) {
                onEdit(i, prop, newVal);
              },
              {
                availableInputDfs,
                newListValueDefault,
                analysisId,
              }
            )}
          </div>
        );
      })}
    </div>
  );
}
