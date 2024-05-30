import setupBaseUrl from "$utils/setupBaseUrl";
import { Button, Input, Modal, Select, message } from "antd";
import {
  arrayOfObjectsToObject,
  breakLinesPretty,
  createPythonFunctionInputString,
  easyToolInputTypes,
  forcedAnnotation,
  mergeClassNames,
  preventModifyTargetRanges,
  snakeCase,
  toolboxDisplayNames,
} from "$utils/utils";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import ReactCodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { MdDeleteOutline } from "react-icons/md";
import { Range, RangeSet, RangeValue } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { classname } from "@uiw/codemirror-extensions-classname";
import { HiSparkles } from "react-icons/hi2";
const { TextArea } = Input;

const addToolEndpoint = setupBaseUrl("http", "add_tool");
const generateToolCodeEndpoint = setupBaseUrl("http", "generate_tool_code");
const skipImages = false;

export default function AddTool({ toolbox, onAddTool }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [toolFunctionBody, setToolFunctionBody] = useState(
    "\n  #\n  # YOUR FUNCTION BODY HERE\n  #\n  pass\n"
  );

  const [toolInputs, setToolInputs] = useState([]);
  const [toolDefStatement, setToolDefStatement] = useState("");

  const [toolReturnStatement, setToolReturnStatement] = useState("");

  const [generateToolCodeLoading, setGenerateToolCodeLoading] = useState(false);
  const getReadOnlyRanges = useCallback(
    // we want to make the function definition, the function doctstring
    // and the return statement read only inside of codemirror
    // this function uses the toolDefStatement, toolFunctionBody and toolReturnStatement
    // to create "read only text ranges" (a codemirror internal thing)
    // which is used in conjunction with the preventModifyTargetRanges function
    // which checks if a range is read only and prevents modification
    (editorState) => {
      return RangeSet.of([
        new Range(0, toolDefStatement.length, new RangeValue(toolDefStatement)),
        new Range(
          toolDefStatement.length + toolFunctionBody.length,
          editorState.doc.length,
          new RangeValue(toolReturnStatement)
        ),
      ]);
    },
    [toolDefStatement, toolReturnStatement, toolFunctionBody]
  );

  const classnameCodeMirrorExtension = useMemo(
    // code mirror extension
    // adds class names to def statements and return statements (read only ranges)
    // in case we want to style them differently later
    () =>
      classname({
        add: (lineNumber) => {
          if (lineNumber <= toolDefStatement.split("\n").length) {
            return "def-line";
          }
          if (
            lineNumber >=
            toolDefStatement.split("\n").length +
              toolFunctionBody.split("\n").length -
              1
          ) {
            return "return-line";
          }
        },
      }),
    [toolDefStatement, toolReturnStatement, toolFunctionBody]
  );

  const [toolOutputs, setToolOutputs] = useState([]);
  const [toolName, setToolName] = useState("New Tool");
  const [toolDocString, setToolDocString] = useState("This tool does XX");
  const editor = useRef();

  const mandatoryInputs = [
    {
      name: "global_dict",
      description: "Stores all previous outputs from the plan",
      type: "dict",
    },
    {
      name: "**kwargs",
    },
  ];

  const handleSubmit = useCallback(async () => {
    // function_name = data.get("function_name")
    // description = data.get("description")
    // code = data.get("code")
    // inputs = data.get("inputs")
    // outputs = data.get("outputs")
    // tool_name = data.get("tool_name")
    // toolbox = data.get("toolbox")

    const data = {
      tool_name: toolName,
      function_name: snakeCase(toolName),
      description: toolDocString,
      code: toolDefStatement + toolFunctionBody + toolReturnStatement,
      input_metadata: arrayOfObjectsToObject(toolInputs, "name"),
      output_metadata: toolOutputs,
      toolbox: toolbox,
      no_code: false,
    };

    const res = await fetch(addToolEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    }).then((response) => response.json());

    console.log(res);

    if (res.success) {
      message.success(`Tool ${toolName} added successfully`);
      setModalOpen(false);
      // clear the form
      setToolName("");
      setToolDocString("");
      setToolInputs([]);
      setToolOutputs([]);
      setToolFunctionBody("\n  #\n  # YOUR FUNCTION BODY HERE\n  #\n  pass\n");

      onAddTool(data);
    } else {
      message.error(
        `Failed to add tool ${toolName}. Error: ${res.error_message}`
      );
    }
  }, [toolDefStatement, toolFunctionBody, toolReturnStatement]);

  useEffect(() => {
    let baseIndent = "  ";
    // def tool_name_in_snake_case
    let newDefStr = "async def " + snakeCase(toolName) + "(";
    // add toolinputs to newDefStr
    // inputs will have name, type and description
    // def function(
    //  p1: p1_type # p1_description,
    //  p2: p2_type # p2_description
    // )
    const allInputs = [...toolInputs, ...mandatoryInputs];
    allInputs.forEach((input, idx) => {
      if (idx === 0) newDefStr += "\n";
      newDefStr += createPythonFunctionInputString(input) + "\n";
    });

    newDefStr += "):";

    // add doc string
    newDefStr +=
      `\n${baseIndent.repeat(1)}"""\n${baseIndent.repeat(1)}` +
      breakLinesPretty(toolDocString) +
      `\n${baseIndent.repeat(1)}"""`;

    let newReturnStr =
      baseIndent.repeat(1) +
      "return {\n" +
      baseIndent.repeat(3) +
      '"outputs": [\n';
    toolOutputs.forEach((output, idx) => {
      newReturnStr += baseIndent.repeat(4) + "{\n";
      newReturnStr += output.description
        ? baseIndent.repeat(5) + "# " + output.description + "\n"
        : "";
      newReturnStr += baseIndent.repeat(5) + '"data": ' + output.name + ",\n";
      if (!skipImages) {
        newReturnStr += baseIndent.repeat(5) + '"chart_images": [\n';
        output.chart_images.forEach((chartImage, imageIdx) => {
          newReturnStr += baseIndent.repeat(6) + "{\n";
          newReturnStr +=
            baseIndent.repeat(7) + '"name": "' + chartImage.name + '",\n';
          newReturnStr += baseIndent.repeat(6) + "},\n";
        });
        newReturnStr += baseIndent.repeat(5) + "],\n";
        newReturnStr += baseIndent.repeat(4) + "},\n";
      }
    });

    newReturnStr += "    ],\n  }";

    setToolDefStatement(newDefStr);
    setToolReturnStatement(newReturnStr);
  }, [toolInputs, toolName, toolOutputs, toolDocString]);

  const handleGenerateToolCode = useCallback(async () => {
    if (generateToolCodeLoading) return;
    try {
      setGenerateToolCodeLoading(true);
      // check tool inputs and outputs
      // empty inputs are fine (maybe they want to use some api)
      // empty outputs are not fine
      // every input should have a name
      // every input should have a type
      // every input should have a description
      // every output should have a name
      // every output should have a description
      // every output should have a type

      if (!toolName) {
        message.error("Tool name can't be empty");
        return false;
      }
      if (!toolDocString) {
        message.error("Tool description can't be empty");
        return false;
      }
      if (!toolOutputs.length) {
        message.error("Tool must have at least one output");
        return false;
      }
      if (!toolOutputs.every((output) => output.name)) {
        message.error("Every output must have a name");
        return false;
      }
      if (!toolOutputs.every((output) => output.description)) {
        message.error("Every output must have a description");
        return false;
      }
      if (!toolOutputs.every((output) => output.type)) {
        message.error("Every output must have a type");
        return false;
      }
      if (!toolInputs.every((input) => input.name)) {
        message.error("Every input must have a name");
        return false;
      }
      if (!toolInputs.every((input) => input.description)) {
        message.error("Every input must have a description");
        return false;
      }
      if (!toolInputs.every((input) => input.type)) {
        message.error("Every input must have a type");
        return false;
      }

      const resp = await fetch(generateToolCodeEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tool_name: toolName,
          tool_description: toolDocString,
          function_name: snakeCase(toolName),
          def_statement: toolDefStatement,
          return_statement: toolReturnStatement,
          toolbox: toolbox,
        }),
      }).then((response) => response.json());

      if (!resp.success || !resp.generated_code) {
        message.error(
          "Failed to generate code. Error: " + resp.error_message ||
            "Unknown error"
        );
      } else {
        // remove the function definition and return statement
        // and set the function body to the generated code
        const generatedFunctionBody = resp.generated_code
          .replace(toolDefStatement, "")
          .replace(toolReturnStatement, "");
        // make sure there's a difference in length = length of def + return
        // and the length of the generated code

        console.log(resp);
        console.log(generatedFunctionBody);
        if (
          generatedFunctionBody.length +
            toolDefStatement.length +
            toolReturnStatement.length !==
          resp.generated_code.length
        ) {
          throw new Error(
            "Generated code has incorrect def and return statements"
          );
        } else {
          setToolFunctionBody(generatedFunctionBody);
        }
      }
    } catch (e) {
      message.error("Failed to generate code. Error: " + e);
    } finally {
      setGenerateToolCodeLoading(false);
    }
  }, [
    toolName,
    toolDocString,
    toolInputs,
    toolDefStatement,
    toolReturnStatement,
    toolOutputs,
    toolbox,
  ]);

  console.log(toolFunctionBody);

  return (
    <>
      <div
        className="tool rounded mr-3 mb-3  bg-blue-50 border border-blue-400 flex items-center p-3 cursor-pointer hover:shadow-lg"
        onClick={() => setModalOpen(true)}
      >
        <div className="flex items-center  justify-center text-blue-500">
          <span className="">
            <p className="m-0">+</p>
          </span>
        </div>
      </div>
      <Modal
        open={modalOpen}
        onCancel={(ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          setModalOpen(null);
        }}
        footer={null}
        centered
        className={"w-10/12 overflow-scroll"}
        rootClassName="feedback-modal"
      >
        <div className="add-tool-modal">
          <h1 className="text-lg font-bold mb-4">
            Add a tool to the {toolboxDisplayNames[toolbox]} toolbox
          </h1>
          <div className="flex flex-row">
            <div className="w-6/12 mr-6">
              <div className="mb-4">
                <h2 className="text-sm uppercase font-light mb-2">Tool name</h2>
                <Input
                  type="text"
                  rootClassName="mb-2 text-gray-600 font-mono"
                  placeholder="Tool name"
                  status={toolName ? "success" : "error"}
                  onChange={(ev) => setToolName(ev.target.value)}
                  value={toolName}
                />
                <h2 className="text-sm uppercase font-light mb-2">
                  Tool description
                </h2>
                <TextArea
                  type="text"
                  rootClassName="mb-2 text-gray-600 font-mono"
                  placeholder="What does this tool do?"
                  status={toolDocString ? "success" : "error"}
                  onChange={(ev) => setToolDocString(ev.target.value)}
                  value={toolDocString}
                />
              </div>
              <div className="tool-inputs mb-8">
                <h2 className="text-sm uppercase font-light mb-2">Inputs</h2>
                {!toolInputs.length ? (
                  <></>
                ) : (
                  <div className="tool-inputs-headings flex flex-row text-xs text-gray-400 mb-2 font-light">
                    <div className="w-3/12">Type</div>
                    <div className="w-3/12">Name</div>
                    <div className="w-6/12">Description</div>
                  </div>
                )}
                {toolInputs.map((input, idx) => {
                  return (
                    <div
                      className="tool-input mb-4 text-xs flex flex-row relative items-start border-b pb-2 border-b-gray-100"
                      key={idx}
                    >
                      <Select
                        defaultValue={input.type}
                        rootClassName="mr-3 w-3/12 font-mono text-gray-600"
                        popupClassName="text-gray-600"
                        onChange={(val, option) => {
                          const newToolInputs = toolInputs.slice();
                          newToolInputs[idx].type = option.value;
                          setToolInputs(newToolInputs);
                        }}
                        options={Object.keys(easyToolInputTypes).map((type) => {
                          return {
                            label: easyToolInputTypes[type],
                            value: type,
                          };
                        })}
                      />

                      <Input
                        status={
                          (input.name &&
                            // make sure not duplicated
                            Object.values(toolInputs).filter(
                              (inp) => inp.name === input.name
                            ).length === 1) ||
                          "error"
                        }
                        type="text"
                        className="w-3/12 mr-3 font-mono text-gray-600"
                        placeholder="Input name can't be empty"
                        value={input.name}
                        onChange={(ev) => {
                          const newToolInputs = toolInputs.slice();
                          newToolInputs[idx].name = ev.target.value;
                          setToolInputs(newToolInputs);
                        }}
                      />

                      <TextArea
                        type="text"
                        className="w-6/12 font-mono text-gray-600"
                        status={input.description ? "success" : "error"}
                        placeholder="A good input description ensures good performance"
                        value={input.description}
                        onChange={(ev) => {
                          const newToolInputs = toolInputs.slice();
                          newToolInputs[idx].description = ev.target.value;
                          setToolInputs(newToolInputs);
                        }}
                      />

                      <p
                        className=" mr-1  flex justify-center items-center rounded-full cursor-pointer w-4 h-4 top-0 -left-5"
                        onClick={() => {
                          const newToolInputs = toolInputs.slice();
                          newToolInputs.splice(idx, 1);
                          setToolInputs(newToolInputs);
                        }}
                      >
                        <MdDeleteOutline
                          className="fill-gray-400 hover:fill-rose-400"
                          size={40}
                          // strokeWidth={1}
                          stroke="red"
                        />
                      </p>
                    </div>
                  );
                })}
                <Button
                  type="primary"
                  className="bg-gray-100 text-gray-500 hover:bg-blue-400 hover:text-white font-mono"
                  onClick={() => {
                    const nm = "input_" + (toolInputs.length + 1);
                    setToolInputs([
                      ...toolInputs,
                      {
                        name: nm,
                        type: "str",
                        description: "",
                      },
                    ]);
                  }}
                >
                  Add input
                </Button>
              </div>
              <div className="tool-outputs ">
                <h2 className="text-sm uppercase font-light mb-2">Outputs</h2>
                {!toolOutputs.length ? (
                  <></>
                ) : (
                  <div className="tool-outputs-headings flex flex-row relative items-start text-xs text-gray-400 mb-2 font-light">
                    <div className="w-3/12">Name</div>
                    {!skipImages && <div className="w-3/12">Images</div>}
                    <div className="w-6/12">Description</div>
                  </div>
                )}
                {toolOutputs.map((output, idx) => {
                  return (
                    <div
                      className="tool-output mb-4 text-xs flex flex-row relative items-start"
                      key={idx}
                    >
                      <Input
                        type="text"
                        className="mr-3 w-3/12 font-mono"
                        placeholder="Output name"
                        value={output.name}
                        onChange={(ev) => {
                          const newToolOutputs = [...toolOutputs];
                          newToolOutputs[idx].name = ev.target.value;
                          setToolOutputs(newToolOutputs);
                        }}
                      />

                      {!skipImages && (
                        <div className="tool-images flex flex-row flex-wrap border rounded-md w-3/12 mr-3 border-gray-300">
                          {output.chart_images.map((chartImage, imageIdx) => {
                            return (
                              <div
                                className="tool-image font-mono  cursor-pointer m-1 rounded flex items-center "
                                key={imageIdx}
                              >
                                <Input
                                  htmlSize={chartImage.name.length}
                                  className="cursor-text bg-gray-100 text-gray-500 font-mono inline"
                                  onChange={(ev) => {
                                    const newToolOutputs = [...toolOutputs];
                                    newToolOutputs[idx].chart_images[
                                      imageIdx
                                    ].name = ev.target.value;
                                    setToolOutputs(newToolOutputs);
                                  }}
                                  defaultValue={chartImage.name}
                                />
                                <MdDeleteOutline
                                  className="fill-gray-400 hover:fill-rose-400"
                                  size={15}
                                  onClick={() => {
                                    const newToolOutputs = [...toolOutputs];
                                    newToolOutputs[idx].chart_images.splice(
                                      imageIdx,
                                      1
                                    );
                                    setToolOutputs(newToolOutputs);
                                  }}
                                />
                              </div>
                            );
                          })}
                          <div
                            className="add-tool-image bg-gray-100 text-gray-500 hover:bg-blue-400 hover:text-white cursor-pointer p-1 px-3 m-1 rounded flex items-center"
                            onClick={() => {
                              const newToolOutputs = [...toolOutputs];
                              newToolOutputs[idx].chart_images.push({
                                name:
                                  "image_" +
                                  toolOutputs[idx].chart_images.length,
                              });
                              setToolOutputs(newToolOutputs);
                            }}
                          >
                            +
                          </div>
                        </div>
                      )}
                      <TextArea
                        type="text"
                        className="w-6/12 font-mono text-gray-600"
                        placeholder="A good output description ensures good performance"
                        value={output.description}
                        onChange={(ev) => {
                          const newToolOutputs = [...toolOutputs];
                          newToolOutputs[idx].description = ev.target.value;
                          setToolOutputs(newToolOutputs);
                        }}
                      />

                      <p
                        className=" mr-1 flex justify-center items-center rounded-full cursor-pointer w-4 h-4 top-0 -left-5 self-center	"
                        onClick={() => {
                          const newToolOutputs = [...toolOutputs];
                          newToolOutputs.splice(idx, 1);
                          setToolOutputs(newToolOutputs);
                        }}
                      >
                        <MdDeleteOutline
                          className="fill-gray-400 hover:fill-rose-400"
                          size={40}
                          // strokeWidth={1}
                          stroke="red"
                        />
                      </p>
                    </div>
                  );
                })}
                <Button
                  type="primary"
                  className="bg-gray-100 text-gray-500 hover:bg-blue-400 hover:text-white font-mono"
                  onClick={() => {
                    setToolOutputs([
                      ...toolOutputs,
                      {
                        name: "output_" + toolOutputs.length,
                        description: "",
                        type: "pandas.core.frame.DataFrame",
                        chart_images: [],
                      },
                    ]);
                  }}
                >
                  Add output
                </Button>
              </div>
            </div>
            <div className="add-code w-6/12">
              <div className="flex flex-row mb-2">
                <h2 className="grow text-sm uppercase font-light">Code</h2>
                <div
                  className={mergeClassNames(
                    "border border-gray-100 cursor-pointer px-1 rounded-md group shadow-sm text-xl flex items-center",
                    "hover:border-gray-300 hover:border-transparent hover:bg-yellow-400"
                  )}
                  onClick={handleGenerateToolCode}
                >
                  <HiSparkles className="text-yellow-400 group-hover:text-white" />
                </div>
              </div>
              <div className={"relative "}>
                <ReactCodeMirror
                  ref={editor}
                  className={
                    "*:outline-0 *:focus:outline-0 " +
                    (generateToolCodeLoading ? "opacity-15" : "")
                  }
                  // refresh if the toolDefStatement or toolReturnStatement changes
                  key={
                    toolDefStatement +
                    toolReturnStatement +
                    "-" +
                    generateToolCodeLoading
                  }
                  value={
                    toolDefStatement + toolFunctionBody + toolReturnStatement
                  }
                  extensions={[
                    python(),
                    preventModifyTargetRanges(getReadOnlyRanges),
                    classnameCodeMirrorExtension,
                    EditorView.lineWrapping,
                  ]}
                  basicSetup={{
                    lineNumbers: false,
                    highlightActiveLine: false,
                  }}
                  editable={!generateToolCodeLoading}
                  language="python"
                  onChange={(val) => {
                    console.log(val);
                    // remove toolDefStatement from the start and
                    // toolReturnStatement from the end
                    // and set the funciton body to the tool code
                    setToolFunctionBody(
                      val
                        .replace(toolDefStatement, "")
                        .replace(toolReturnStatement, "")
                    );
                  }}
                />
                {generateToolCodeLoading && (
                  <div className="w-full h-full rounded-md absolute left-0 top-0 flex bg-yellow-400 bg-opacity-70 items-center justify-center align-center">
                    <div className="flex items-center p-2">
                      <span className="animate-bounce mr-3 inline-flex h-2 w-2 rounded-full bg-yellow-500"></span>
                      <span className="animate-bounce mr-3 inline-flex h-2 w-2 rounded-full bg-yellow-500"></span>
                      <span className="animate-bounce inline-flex h-2 w-2 rounded-full bg-yellow-500"></span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="text-right mt-10">
          <Button
            type="primary"
            className="font-mono"
            onClick={handleSubmit}
            disabled={generateToolCodeLoading}
          >
            Submit
          </Button>
        </div>
      </Modal>
    </>
  );
}
