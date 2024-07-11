import React, { useCallback, useContext, useMemo } from "react";
import { easyToolInputTypes } from "$utils/utils";
import {
  TextArea,
  SingleSelect,
  Input,
  MessageManagerContext,
} from "$ui-components";
import TrashIcon from "$components/icons/TrashIcon";
import { PlusCircleIcon } from "@heroicons/react/20/solid";

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

export const inputTypeToUI = {
  list: (
    inputName,
    initialValue,
    onEdit,
    config = { messageManager: null, newListValueDefault: "New Value" }
  ) => {
    if (!initialValue || !Array.isArray(initialValue)) initialValue = [];

    return (
      <span className="tool-input-value tool-input-type-list">
        <span className="list-bracket">[</span>
        {initialValue.map((val, i) => {
          return (
            <span key={inputName}>
              <Input
                value={val}
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
  str: (inputName, initialValue, onEdit, config = { messageManager: null }) => {
    if (!initialValue) initialValue = "";
    return (
      <TextArea
        rootClassNames="tool-input-value md:w-80"
        textAreaClassNames="resize-none"
        defaultRows={1}
        value={initialValue || ""}
        onChange={(ev) => {
          onEdit(inputName, ev.target.value);
        }}
      />
    );
  },
  bool: (
    inputName,
    initialValue,
    onEdit,
    config = { messageManager: null }
  ) => {
    return (
      <SingleSelect
        placeholder="Select a value"
        value={initialValue || null}
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
  int: (inputName, initialValue, onEdit, config = { messageManager: null }) => (
    <TextArea
      rootClassNames="tool-input-value md:w-80"
      textAreaClassNames="resize-none"
      defaultRows={1}
      value={initialValue || ""}
      onChange={(ev) => {
        onEdit(inputName, parseFloat(ev.target.value));
      }}
    />
  ),
  float: (
    inputName,
    initialValue,
    onEdit,
    config = { messageManager: null }
  ) => (
    <TextArea
      rootClassNames="tool-input-value md:w-80"
      textAreaClassNames="resize-none"
      defaultRows={1}
      value={initialValue}
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
      setSelectedInputDf: () => {},
    }
  ) => {
    const options =
      config?.availableInputDfs?.map((df) => {
        return { label: df, value: "global_dict." + df };
      }) || [];

    return (
      <SingleSelect
        allowCreateNewOption={false}
        size="small"
        placeholder="Select a value"
        onChange={(val) => {
          onEdit(inputName, val);
        }}
        value={initialValue}
        optionRenderer={(option, focus, selected) => {
          return (
            <div
              className="p-2 text-sm bg-white text-gray-500 rounded-md border-l-8 border-l-lime-400"
              onMouseOver={(ev) => onHover(ev, option.label, config.analysisId)}
              onMouseOut={(ev) =>
                onHoverOut(ev, option.label, config.analysisId)
              }
            >
              <span>{option?.label}</span>
            </div>
          );
        }}
        // tagRender={(option) => {
        //   return (
        //     <div
        //       className="tool-input-data-value"
        //       onMouseOver={(ev) => onHover(ev, option.label, config.analysisId)}
        //       onMouseOut={(ev) =>
        //         onHoverOut(ev, option.label, config.analysisId)
        //       }
        //     >
        //       <span>{option?.label}</span>
        //     </div>
        //   );
        // }}
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
      <SingleSelect
        value={initialValue}
        key={config.toolRunId + "_" + inputName}
        size="small"
        popupClassName="tool-input-value-dropdown"
        options={options}
        placeholder="Select a column name"
        onChange={(val) => {
          onEdit(inputName, val);
        }}
      />
    );
  },
  DBColumnList: (
    inputName,
    initialValue,
    onEdit,
    config = {
      messageManager: null,
      availableParentColumns: [],
      toolRunId: "",
      type: "",
    }
  ) => {
    // find the min and max from the type
    // usually exists as DBColumnList_min_max
    // where max is optional
    const minMax = config.type.split("_").slice(1);
    const min = +minMax[0];
    if (minMax.length === 1) minMax.push(minMax[0]);
    let max = +minMax[1];

    // if max is 0, then it's infinity
    if (max === 0) {
      max = Infinity;
    }

    // dropdown with available columns
    const options =
      config?.availableParentColumns?.map((column) => {
        return { label: column.title, value: column.title };
      }) || [];

    // similar to list, just that the new value and existing values are dropdowns
    if (!initialValue) initialValue = Array(min).fill("");
    return (
      <span className="tool-input-value tool-input-type-list tool-input-type-column-list">
        <span className="list-bracket">[</span>
        {initialValue.map((val, i) => {
          return (
            <span key={config.toolRunId + "_" + inputName + "_" + i}>
              <SingleSelect
                value={val}
                size="small"
                placeholder="Select a column name"
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
                <TrashIcon
                  onClick={() => {
                    // if the length is already at min, don't remove
                    if (initialValue.length <= min) {
                      config.messageManager?.error(
                        `${inputName} requires at least ${min} column(s)`
                      );
                      return;
                    }

                    onEdit(
                      inputName,
                      initialValue.filter((v, j) => j !== i)
                    );
                  }}
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
          <PlusCircleIcon
            className="w-3 h-3"
            onClick={() => {
              // if the length is already at max, don't add
              if (initialValue.length >= max) {
                messageManager?.error(
                  `Maximum number of columns (${max}) reached for ${inputName}`
                );
                return;
              }
              onEdit(inputName, [...initialValue, ""]);
            }}
          ></PlusCircleIcon>
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
      messageManager: null,
      availableParentColumns: [],
      toolRunId: "",
      inputMetadata: {},
    }
  ) => {
    const options = config?.inputMetadata?.[inputName]?.default || [];

    return (
      <SingleSelect
        value={initialValue}
        size="small"
        popupClassName="tool-input-value-dropdown"
        options={options.map((option) => {
          return { label: option, value: option };
        })}
        placeholder="Select a value"
        onChange={(val) => {
          onEdit(inputName, val);
        }}
      />
    );
  },
};

function sanitizeInputType(type) {
  if (typeof type === "string" && type.startsWith("DBColumnList_")) {
    return "DBColumnList";
  }
  return type;
}

export function AddStepInputList({
  toolRunId,
  analysisId,
  toolMetadata,
  inputs = {},
  onEdit = () => {},
  newListValueDefault = "",
  parentNodeData = {},
  autoFocus = true,
}) {
  const messageManager = useContext(MessageManagerContext);

  const inputMetadata = toolMetadata?.input_metadata || {};
  const ctr = useCallback(
    (node) => {
      if (!autoFocus) return;
      if (node) {
        // hacky as f from here: https://github.com/facebook/react/issues/20863
        // my guess is requestAnimationFrame is needed to ensure browser is finished painting the DOM
        // before we try to focus
        window.requestAnimationFrame(() => {
          setTimeout(() => {
            // put the focus on the first input on first render
            const el = node.querySelector(
              "div.tool-input-value, input.tool-input-value"
            );

            if (!el) return;
            el.focus();
          }, 0);
        });
      }
    },
    [toolRunId, toolMetadata]
  );

  const availableColumns = useMemo(() => {
    // check if any of the inputs is global_dict.something
    if (!inputs) return [];
    let avail = [];

    Object.keys(inputs).forEach((input_name) => {
      const input = inputs[input_name];

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
    <div className="" key={toolRunId} ref={ctr}>
      {Object.keys(inputs).map((input_name, i) => {
        const sanitizedType = sanitizeInputType(
          inputMetadata[input_name]?.type
        );
        const input = inputs[input_name];

        return (
          <div
            key={i + "_" + toolRunId}
            className="font-mono flex flex-row flex-wrap gap-3 items-center *:my-1 pb-4 text-xs"
          >
            <span className="">
              <span className="rounded-md p-1 bg-gray-200 text-gray-400 mr-2">
                {easyToolInputTypes[sanitizedType] || sanitizedType}
              </span>
              <span className="font-bold">
                {inputMetadata[input_name].name}
              </span>
            </span>
            {inputTypeToUI[sanitizedType] &&
              inputTypeToUI[sanitizedType](
                inputMetadata[input_name]?.name,
                input,
                function (prop, newVal) {
                  onEdit(prop, newVal);
                },
                {
                  availableParentColumns: availableColumns,
                  availableInputDfs: Object.keys(parentNodeData),
                  newListValueDefault,
                  analysisId,
                  toolRunId,
                  inputMetadata,
                  type: inputMetadata[input_name].type,
                  messageManager,
                }
              )}
          </div>
        );
      })}
    </div>
  );
}
