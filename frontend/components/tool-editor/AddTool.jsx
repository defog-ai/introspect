import { addTool } from "$utils/utils";
import { useCallback, useContext, useMemo, useRef, useState } from "react";
import { DefineTool } from "./DefineTool";

import {
  MessageManagerContext,
  Modal,
  Input,
  Button,
  SpinningLoader,
  SingleSelect,
} from "@defogdotai/agents-ui-components/core-ui";

import NewToolCodeEditor from "./NewToolCodeEditor";
import setupBaseUrl from "$utils/setupBaseUrl";
import { twMerge } from "tailwind-merge";
import { AnalysisAgent, Setup } from "@defogdotai/agents-ui-components/agent";
import ErrorBoundary from "$components/layout/ErrorBoundary";
import { ToolFlow } from "./ToolFlow";

const createToolText = "Create tool";

export function AddTool({
  allTools = {},
  apiEndpoint,
  onAddTool = (...args) => {},
  apiKeyNames = [],
}) {
  const generateToolCodeEndpoint = setupBaseUrl(
    "http",
    "generate_or_edit_tool_code"
  );

  const [modalOpen, setModalOpen] = useState(false);
  const [testQuestion, setTestQuestion] = useState("");
  const [tool, setTool] = useState({
    code: "",
    description: "",
    function_name: "",
    input_metadata: {},
    output_metadata: [],
    tool_name: "",
    key_name: apiKeyNames.length ? apiKeyNames[0] : null,
  });

  const [analysisId, setAnalysisId] = useState(crypto.randomUUID());

  const toolName = tool.tool_name;
  const toolDocString = tool.description;
  const generatedCode = tool.code;
  const selectedKeyName = tool.key_name;

  const messageManager = useContext(MessageManagerContext);

  const [loading, setLoading] = useState(false);
  const token = useRef(localStorage.getItem("defogToken"));

  const [currentStep, setCurrentStep] = useState(0);

  const changeStep = (targetStepIdx) => {
    if (targetStepIdx > 0 && (!toolName || !toolDocString || !tool.code)) {
      messageManager.info("Please create the tool first");
      return;
    }

    setCurrentStep(targetStepIdx);
  };

  const createToolBtn = useMemo(() => {
    return (
      <Button
        disabled={!toolName || !toolDocString || loading}
        className="bg-blue-500 hover:bg-blue-600 text-white hover:text-white"
        onClick={() => {
          if (!toolName || !toolDocString) {
            messageManager.error(
              "Please fill in the tool name and description"
            );
            return;
          }

          setTestQuestion(null);
          handleSubmit();
        }}
      >
        {loading ? (
          <div>
            <SpinningLoader classNames="text-gray-300" />
            Creating your tool
          </div>
        ) : (
          createToolText
        )}
      </Button>
    );
  }, [currentStep, toolName, toolDocString, loading]);

  const handleChange = useCallback(
    (prop, val) => {
      try {
        // if prop doesn't exists on the tool, show error
        if (!tool.hasOwnProperty(prop)) {
          throw new Error(`Tool does not have property ${prop}`);
        }
        setTool((t) => ({ ...t, [prop]: val }));
      } catch (e) {
        messageManager.error(e.message);
      }
    },
    [tool, setTool, messageManager]
  );

  const tryAddTool = async () => {
    setLoading(true);
    try {
      const res = await addTool(tool);

      if (res.success) {
        messageManager.success("Tool added successfully");
        onAddTool(tool);
        setModalOpen(false);
      } else {
        messageManager.error(
          "Failed to submit tool" + (res.error_message || "")
        );
      }
    } catch (e) {
      console.error(e);
      messageManager.error("Failed to submit tool" + e.message);
    } finally {
      setLoading(false);
    }
  };

  // fixToolRequest is true when the user is trying to fix the tool
  // if they re click the create tool button in the first tab, we need to re generate it from scratch
  const handleSubmit = async (userQuestion = null, fixToolRequest = false) => {
    setLoading(true);
    try {
      // if this tool name exists in the library, give an error
      Object.values(allTools).some((t) => {
        if (t.tool_name === toolName) {
          throw new Error(
            `Another tool with the name ${toolName} already exists in the library. Please choose a different name.`
          );
        }
      });
      const response = await fetch(generateToolCodeEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tool_name: toolName,
          tool_description: toolDocString,
          user_question: userQuestion,
          current_code: fixToolRequest ? generatedCode || null : null,
          key_name: selectedKeyName || apiKeyNames[0],
        }),
      }).then((res) => res.json());

      if (!response.success) {
        throw new Error(
          "Failed to generate tool code. " + (response.error_message || "")
        );
      }

      const newTool = { ...tool };

      newTool.code = response.generated_code;
      newTool.function_name = response.function_name;
      newTool.input_metadata = response.input_metadata;
      newTool.output_metadata = response.output_metadata;

      setTool(newTool);
      setCurrentStep(1);
    } catch (error) {
      messageManager.error(error);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const steps = useMemo(() => {
    return [
      {
        title: "Describe your tool",
        content: (
          <div className="sm:block min-h-80">
            <p className="text-sm my-4 text-gray-500">
              The model needs this information to generate your tool.
            </p>
            <DefineTool
              disabled={loading}
              toolName={toolName}
              handleChange={handleChange}
              toolDocString={tool.description}
            />
            <SingleSelect
              label="Which database do you want to test this tool on?"
              disabled={loading}
              options={apiKeyNames.map((name) => ({
                label: name,
                value: name,
              }))}
              allowCreateNewOption={false}
              allowClear={false}
              rootClassNames="mb-4 text-gray-600"
              placeholder="Select Database"
              onChange={(val) => handleChange("key_name", val)}
              value={tool.key_name}
            />
            {toolDocString && toolName && createToolBtn}
          </div>
        ),
      },
      {
        title: "Test",
        content: tool.code ? (
          <>
            <div className="text-sm gap-8 text-gray-500 lg:flex lg:flex-row-reverse">
              <ul className="my-4 w-full lg:w-1/2 *:my-1">
                <li className="list-disc">
                  We've created your tool based on the provided name and
                  description. You can test the tool with a question by typing
                  it in the search box on the right.
                </li>
                <li className="list-disc">
                  On the left, you can either edit your tool's code directly, or
                  suggest a change in the search box to generate a new version
                  of your tool.
                </li>
                <li className="list-disc">
                  If you changed your mind, go back to the describe step and
                  change the tool's name or description and click "
                  {createToolText}" again.
                </li>
                <li className="list-disc">
                  Once you're satisfied, click "Save" to add the tool to your
                  library.
                </li>
              </ul>
              <div className="grow lg:w-1/2 my-4">
                <ErrorBoundary>
                  <ToolFlow
                    toolName={tool.tool_name}
                    inputMetadata={tool.input_metadata}
                    outputMetadata={tool.output_metadata}
                  />
                </ErrorBoundary>
              </div>
            </div>
            <div className="divide-x mb-8 lg:h-96 flex flex-row flex-wrap lg:flex-nowrap gap-1">
              <div className="w-full overflow-scroll relative px-2 bg-gray-800 lg:w-5/12">
                <div
                  className={
                    "w-full pt-2 pb-3 px-6 text-sm text-gray-500 sticky top-0 z-50 bg-gray-600 border-b border-gray-600 rounded-b-3xl shadow-md mb-4"
                  }
                >
                  <Input
                    placeholder="Suggest a change and press Enter to generate new code for your tool"
                    disabled={loading}
                    onPressEnter={(ev) => {
                      if (!ev.target.value) {
                        messageManager.error("Suggestion can't be empty");
                        return;
                      }

                      handleSubmit(ev.target.value, true);
                      ev.target.value = "";
                    }}
                  ></Input>
                </div>
                {loading ? (
                  <div className="flex flex-col items-center justify-center text-xs text-gray-400">
                    <SpinningLoader classNames="text-gray-400 mb-2" />
                    Generating new code
                  </div>
                ) : (
                  <NewToolCodeEditor
                    className="w-full"
                    editable={!loading}
                    toolCode={tool.code}
                    onChange={(v) => handleChange("code", v)}
                  />
                )}
              </div>
              <div
                className={twMerge(
                  "relative w-full mt-8 px-2 pb-2 lg:mt-0 lg:w-7/12 bg-gray-200 overflow-scroll"
                )}
              >
                <div
                  className={twMerge(
                    "w-full text-sm text-gray-500 sticky top-0 z-50 bg-gray-100 shadow-md pt-2 pb-3 px-6 rounded-b-3xl mb-4 border-b border-gray-400 flex flex-row items-end gap-2"
                  )}
                >
                  <SingleSelect
                    label="Database"
                    disabled={loading}
                    options={apiKeyNames.map((name) => ({
                      label: name,
                      value: name,
                    }))}
                    allowCreateNewOption={false}
                    allowClear={false}
                    placeholder="Select Database"
                    onChange={(val) => handleChange("key_name", val)}
                    value={tool.key_name}
                  />
                  <Input
                    label="Test question"
                    rootClassNames="grow"
                    inputClassNames="h-9"
                    placeholder={
                      testQuestion
                        ? "Test with another question. Type here and press Enter."
                        : "Test your tool with a question. Type here and press Enter."
                    }
                    disabled={loading}
                    onPressEnter={(ev) => {
                      if (!ev.target.value) {
                        messageManager.error("Query can't be empty");
                        return;
                      }

                      // create a new analysis id and reset the test question
                      setAnalysisId(crypto.randomUUID());
                      setTestQuestion(ev.target.value);
                      ev.target.value = "";
                    }}
                  ></Input>
                </div>

                {testQuestion ? (
                  <Setup
                    key={analysisId + "-" + testQuestion}
                    token={token.current}
                    apiEndpoint={apiEndpoint}
                    // these are the ones that will be shown for new csvs uploaded
                    showAnalysisUnderstanding={true}
                    disableMessages={false}
                  >
                    <AnalysisAgent
                      analysisId={analysisId}
                      disabled={loading}
                      keyName={selectedKeyName}
                      plannerQuestionSuffix={` Make sure to use the \`${toolName}\` tool in the analysis.`}
                      extraTools={[
                        {
                          code: tool.code,
                          tool_name: tool.tool_name,
                          tool_description: tool.description,
                          function_name: tool.function_name,
                          input_metadata: tool.input_metadata,
                          output_metadata: tool.output_metadata,
                        },
                      ]}
                      createAnalysisRequestBody={{
                        initialisation_details: {
                          user_question: testQuestion,
                        },
                      }}
                      initiateAutoSubmit={true}
                    />
                  </Setup>
                ) : (
                  <div className="rounded-3xl w-full h-20 flex items-center justify-center text-sm text-gray-400">
                    {loading ? (
                      <div className="flex items-center justify-center">
                        <SpinningLoader classNames="text-gray-400" />
                      </div>
                    ) : (
                      "Ask a quesion above to test your tool"
                    )}
                  </div>
                )}
              </div>
            </div>
            <Button
              className=" px-3 text-white bg-blue-500 border-0 hover:bg-blue-600 hover:text-white"
              onClick={tryAddTool}
              disabled={loading}
            >
              Save your tool
            </Button>
          </>
        ) : (
          <div className="min-h-80 flex items-center justify-center">
            {toolDocString && toolName ? (
              createToolBtn
            ) : (
              <p className="text-sm text-gray-400">
                Please complete the previous step
              </p>
            )}
          </div>
        ),
      },
    ];
  }, [tool, loading, testQuestion, analysisId]);

  return (
    <>
      <div
        className="rounded mr-3 mb-3  bg-blue-50 border border-blue-400 flex items-center p-3 cursor-pointer hover:shadow-lg"
        onClick={() => setModalOpen(true)}
      >
        <div className="flex items-center  justify-center text-blue-500">
          <span className="">
            <p className="m-0">+ New tool</p>
          </span>
        </div>
      </div>

      <Modal
        open={modalOpen}
        onCancel={(ev) => {
          setModalOpen(false);
        }}
        footer={false}
        contentClassNames="max-w-[1500px]"
      >
        <h1 className="text-lg font-bold mb-4">Add a custom tool</h1>

        <div className="grow relative p-2">
          <div className="relative">
            {/* dividing line */}
            <div className="h-[1px] w-full bg-gray-300 absolute top-1/2 z-[2]"></div>
            <div className="z-[3] flex flex-row relative">
              {steps.map((step, idx) => {
                const isActive = idx === currentStep;

                return (
                  <div
                    key={idx}
                    className={twMerge(
                      "grow group cursor-pointer",
                      idx === steps.length - 1 ? "bg-white" : ""
                    )}
                    onClick={() => changeStep(idx)}
                  >
                    <div
                      className={twMerge(
                        "px-4 inline-block bg-white relative justify-self-center",
                        idx === 0 ? "pl-0" : ""
                      )}
                    >
                      <span
                        className={twMerge(
                          "text-sm p-3 rounded-[50%] border text-gray-400 border-gray-200 bg-gray-100 inline-flex items-center justify-center h-4 w-4 mr-2",
                          isActive
                            ? "bg-blue-100 text-blue-500"
                            : "group-hover:bg-gray-200"
                        )}
                      >
                        {idx + 1}
                      </span>
                      <span
                        className={isActive ? "text-blue-500" : "text-gray-400"}
                      >
                        {step.title}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-4">{steps[currentStep].content}</div>
        </div>
      </Modal>
    </>
  );
}
