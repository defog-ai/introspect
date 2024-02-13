import { Input, Select } from "antd";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { MdDeleteOutline, MdOutlineAddBox } from "react-icons/md";
import { easyColumnTypes } from "../../../../utils/utils";

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
        // autoFocus={config?.autoFocus}
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
        // autoFocus={config?.autoFocus}
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
      // autoFocus={config?.autoFocus}
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
      // autoFocus={config?.autoFocus}
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
    config = {
      availableInputDfs: [],
      analysisId: "",
      autoFocus: false,
      setSelectedInputDf: () => {},
    }
  ) => {
    const options =
      config?.availableInputDfs?.map((df) => {
        return { label: df, value: "global_dict." + df };
      }) || [];

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
  DBColumn: (
    inputName,
    initialValue,
    onEdit,
    config = {
      availableParentColumns: [],
      toolRunId: "",
    }
  ) => {
    // dropdown with available columns
    const options =
      config?.availableParentColumns?.map((column) => {
        return { label: column.title, value: column.title };
      }) || [];

    // return
    return (
      <Select
        value={initialValue}
        key={config.toolRunId + "_" + inputName}
        size="small"
        popupClassName="tool-input-value-dropdown"
        options={options}
        placeholder="Select a column name"
        allowClear
        onChange={(val) => {
          onEdit(inputName, val);
        }}
      />
    );
  },
  "list[DBColumn]": (
    inputName,
    initialValue,
    onEdit,
    config = {
      availableParentColumns: [],
      toolRunId: "",
    }
  ) => {
    // dropdown with available columns
    const options =
      config?.availableParentColumns?.map((column) => {
        return { label: column.title, value: column.title };
      }) || [];

    // similar to list, just that the new value and existing values are dropdowns
    if (!initialValue) initialValue = [];
    return (
      <span className="tool-input-value tool-input-type-list tool-input-type-column-list">
        <span className="list-bracket">[</span>
        {initialValue.map((val, i) => {
          return (
            <span key={config.toolRunId + "_" + inputName + "_" + i}>
              <Select
                value={val}
                showSearch
                size="small"
                placeholder="Select a column name"
                allowClear
                popupClassName="tool-input-value-dropdown"
                options={options}
                onChange={(val) => {
                  // replace the value at i with the new value
                  const newVal = initialValue.map((v, j) => {
                    if (i === j) {
                      return val;
                    }
                    return v;
                  });
                  onEdit(inputName, newVal);
                }}
              />
              <div className="list-remove">
                <MdDeleteOutline
                  onClick={() =>
                    onEdit(
                      inputName,
                      initialValue.filter((v, j) => j !== i)
                    )
                  }
                />
              </div>
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
              onEdit(inputName, [...initialValue, ""]);
            }}
          ></MdOutlineAddBox>
        </div>
        <span className="list-bracket">]</span>
      </span>
    );
  },
  DropdownSingleSelect: (
    inputName,
    initialValue,
    onEdit,
    config = {
      availableParentColumns: [],
      toolRunId: "",
      functionSignature: {},
    }
  ) => {
    const options =
      config?.functionSignature?.find((sig) => sig.name === inputName)
        ?.default || [];

    return (
      <Select
        value={initialValue}
        size="small"
        popupClassName="tool-input-value-dropdown"
        options={options.map((option) => {
          return { label: option, value: option };
        })}
        placeholder="Select a value"
        allowClear
        onChange={(val) => {
          onEdit(inputName, val);
        }}
      />
    );
  },
};

export function AddStepInputList({
  toolRunId,
  analysisId,
  toolMetadata,
  inputs = [],
  onEdit = () => {},
  newListValueDefault = "",
  parentNodeData = {},
}) {
  const functionSignature = toolMetadata?.function_signature || [];
  const ctr = useRef(null);

  const availableColumns = useMemo(() => {
    // check if any of the inputs is global_dict.something
    if (!inputs) return [];
    let avail = [];

    inputs.forEach((input) => {
      if (typeof input !== "string") return;
      if (input?.startsWith("global_dict.")) {
        const id = input.split(".")[1];
        const parent = parentNodeData[id];
        if (parent) {
          avail = avail.concat(parent.data.columns);
        }
      }
    });

    return avail;
  }, [inputs, parentNodeData, toolRunId]);

  return (
    <div className="tool-input-list" key={toolRunId} ref={ctr}>
      {inputs.map((input, i) => {
        return (
          <div key={i + "_" + toolRunId} className="tool-input">
            <span className="tool-input-type">
              {easyColumnTypes[functionSignature[i].type] ||
                functionSignature[i].type}
            </span>
            <span className="tool-input-name">{functionSignature[i].name}</span>
            {inputTypeToUI[functionSignature[i].type](
              functionSignature[i].name,
              input,
              function (prop, newVal) {
                onEdit(i, prop, newVal);
              },
              {
                availableParentColumns: availableColumns,
                availableInputDfs: Object.keys(parentNodeData),
                newListValueDefault,
                analysisId,
                toolRunId,
                functionSignature,
              }
            )}
          </div>
        );
      })}
    </div>
  );
}
