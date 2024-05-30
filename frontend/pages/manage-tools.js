import { Button, Modal, message } from "antd";
import Meta from "../components/common/Meta";
import Scaffolding from "../components/common/Scaffolding";
import {
  easyToolInputTypes,
  toolDisplayNames,
  toolboxDisplayNames,
} from "../utils/utils";
import { useEffect, useMemo, useState } from "react";
import AddTool from "../components/docs/AddTool";
import setupBaseUrl from "../utils/setupBaseUrl";

const toggleDisableToolEndpoint = setupBaseUrl("http", "toggle_disable_tool");
const deleteToolEndpoint = setupBaseUrl("http", "delete_tool");

export default function ManageTools() {
  // group tools by "toolbox"
  const [tools, setTools] = useState(null);

  const groupedTools = useMemo(() => {
    if (tools) {
      // group tools by toolbox
      const grouped = {};
      Object.values(tools).forEach((tool) => {
        if (!grouped[tool.toolbox]) {
          grouped[tool.toolbox] = {};
        }
        grouped[tool.toolbox][tool.function_name] = tool;
      });
      return grouped;
    }
    return null;
  }, [tools]);

  console.log(tools, groupedTools);

  const [selectedTool, setSelectedTool] = useState(null);

  const onAddTool = (toolDict) => {
    setTools({
      ...tools,
      [toolDict.function_name]: toolDict,
    });
  };

  useEffect(() => {
    async function fetchTools() {
      const response = await fetch(setupBaseUrl("http", "get_user_tools"), {
        method: "POST",
      });
      const data = (await response.json())["tools"];
      setTools(data);
    }

    fetchTools();
  }, []);

  return (
    <>
      <Meta />
      <Scaffolding id={"add-tools"} userType={"admin"}>
        {!tools || !groupedTools ? (
          <div>Fetching your tools...</div>
        ) : (
          <>
            <Modal
              open={selectedTool ? true : false}
              onCancel={(ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                setSelectedTool(null);
              }}
              footer={null}
            >
              {selectedTool ? (
                <>
                  <h1 className="text-lg mb-2">
                    {tools[selectedTool].tool_name}
                  </h1>
                  <h1 className="text-xs mb-5 text-gray-400 font-mono">
                    {tools[selectedTool].description}
                  </h1>
                  <div className="tool-tags mb-6">
                    <h1 className="text-xs uppercase font-light mb-2">Tags</h1>
                    {tools[selectedTool].disabled ? (
                      <span className="rounded-md font-mono mr-3 text-white bg-pink-300 px-1 py-1 text-xs">
                        Disabled
                      </span>
                    ) : (
                      <span className="rounded-md font-mono mr-3 text-teal-700 bg-teal-200 px-1 py-1 text-xs">
                        Enabled
                      </span>
                    )}
                    {tools[selectedTool].cannot_disable && (
                      <span className="rounded-md font-mono mr-3 text-gray-600 bg-gray-300 px-1 py-1 text-xs">
                        Cannot disable
                      </span>
                    )}
                    {tools[selectedTool].cannot_delete && (
                      <span className="rounded-md font-mono mr-3 text-gray-600 bg-gray-300 px-1 py-1 text-xs">
                        Cannot delete
                      </span>
                    )}
                  </div>
                  <div className="tool-inputs mb-6">
                    <h2 className="text-xs uppercase font-light mb-4">
                      Inputs
                    </h2>
                    {Object.values(tools[selectedTool].input_metadata).map(
                      (input, i) => (
                        <div
                          className="tool-input mb-4 text-xs"
                          key={input.name + "-" + input.type + "-" + i}
                        >
                          <span className="rounded-md border-gray-200 font-mono mr-3 text-gray-400 bg-gray-200 px-1 py-1">
                            {easyToolInputTypes[input["type"]] || input["type"]}
                          </span>
                          <span className="">{input["name"]}</span>
                        </div>
                      )
                    )}
                  </div>
                  <div className="tool-actions mt-10">
                    {!tools[selectedTool].cannot_disable && (
                      <Button
                        type="primary"
                        className="font-mono mr-5"
                        onClick={async () => {
                          const goalStatus = tools[selectedTool].disabled
                            ? "enabled"
                            : "disabled";
                          const res = await fetch(toggleDisableToolEndpoint, {
                            method: "POST",
                            headers: {
                              "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                              function_name: tools[selectedTool].function_name,
                            }),
                          }).then((d) => d.json());

                          if (res.success) {
                            message.success(
                              `Tool ${selectedTool} is now ${goalStatus}`
                            );
                            setTools((prevTools) => {
                              const newTools = { ...prevTools };
                              newTools[selectedTool].disabled =
                                !newTools[selectedTool].disabled;

                              return newTools;
                            });
                          } else {
                            message.error(
                              `Failed to ${goalStatus.slice(0, -1)} tool. ${
                                res.error_message
                                  ? "Error: " + res.error_message
                                  : ""
                              }`
                            );
                          }
                        }}
                      >
                        {tools[selectedTool].disabled
                          ? "Enable tool"
                          : "Disable tool"}
                      </Button>
                    )}
                    {!tools[selectedTool].cannot_delete && (
                      <Button
                        type="primary"
                        className="font-mono mr-5 bg-red"
                        onClick={async () => {
                          const res = await fetch(deleteToolEndpoint, {
                            method: "POST",
                            headers: {
                              "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                              function_name: tools[selectedTool].function_name,
                            }),
                          }).then((d) => d.json());

                          if (res.success) {
                            message.success(
                              `Tool ${selectedTool} is now deleted`
                            );
                            setTools((prevTools) => {
                              const newTools = { ...prevTools };
                              delete newTools[selectedTool];

                              return newTools;
                            });
                            setSelectedTool(null);
                          } else {
                            message.error(
                              `Failed to delete tool. ${
                                res.error_message
                                  ? "Error: " + res.error_message
                                  : ""
                              }`
                            );
                          }
                        }}
                      >
                        Delete tool
                      </Button>
                    )}
                  </div>
                </>
              ) : (
                "Please select a tool"
              )}
            </Modal>

            <div>
              <h1 className="text-2xl font-bold mb-4">Tool management</h1>
              <div className="tool-list">
                {Object.keys(groupedTools).map((toolbox) => {
                  {
                    return (
                      <div key={toolbox}>
                        <h1 className="text-md font-bold mb-4">
                          {toolboxDisplayNames[toolbox]}
                        </h1>
                        <div className="toolbox flex flex-wrap flex-row mb-10">
                          {Object.keys(groupedTools[toolbox]).map((tool) => {
                            return (
                              <div
                                className="tool rounded mr-3 mb-3 bg-gray-50 border border-gray-400 p-3 w-60 cursor-pointer hover:shadow-lg"
                                key={tool}
                                onClick={() => setSelectedTool(tool)}
                              >
                                <div className="tool-name text-md">
                                  {tools[tool].tool_name}
                                </div>
                              </div>
                            );
                          })}

                          <AddTool
                            toolbox={toolbox}
                            onAddTool={onAddTool}
                          ></AddTool>
                        </div>
                      </div>
                    );
                  }
                })}
              </div>
            </div>
          </>
        )}
      </Scaffolding>
    </>
  );
}
