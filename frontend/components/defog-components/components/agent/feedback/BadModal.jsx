import { Button, Modal } from "antd";
import StepsDag from "../../common/StepsDag";
import { useCallback, useEffect, useState } from "react";
import { toolDisplayNames, toolShortNames } from "$utils/utils";

export default function BadModal({
  open,
  setModalVisible,
  analysisId,
  analysisSteps,
  submitFeedback,
}) {
  const [dag, setDag] = useState(null);
  const [dagLinks, setDagLinks] = useState([]);
  const [loading, setLoading] = useState(false);

  const [activeNode, _setActiveNode] = useState(null);

  // extend setActiveNode to prevent changing node when we click an "output" node
  // only change the node when we click a tool node
  const setActiveNode = (node) => {
    if (node.data.isTool) {
      _setActiveNode(node);
    }
  };

  const [comments, _setComments] = useState({
    general: "",
    step_wise: {},
  });

  const handleSubmit = useCallback(async () => {
    setLoading(true);
    const feedbackResponse = await submitFeedback({
      is_correct: false,
      comments: comments,
    });

    setLoading(false);
  }, [analysisId, comments, submitFeedback, setModalVisible]);

  const setComments = (newComments) => {
    _setComments(newComments);
    try {
      localStorage.setItem(
        `analysis-${analysisId}-comments`,
        JSON.stringify(newComments)
      );
    } catch (e) {
      console.error("Error saving comments to local storage", e);
      localStorage.removeItem(`analysis-${analysisId}-comments`);
    }
  };

  useEffect(() => {
    let parsedComments = {};

    try {
      // first check local storage
      const storedComments = localStorage.getItem(
        `analysis-${analysisId}-comments`
      );

      if (storedComments) {
        // try to parse it
        parsedComments = JSON.parse(storedComments);
      }
    } catch (e) {
      console.error(
        "Error parsing comments from local storage. Starting fresh comments object",
        e
      );
      parsedComments = {};
    }

    // start a comments object with the parsed comments so far
    const newComments = {
      general: parsedComments["general"] || "",
      step_wise: parsedComments["step_wise"] || {},
    };

    analysisSteps.forEach((step) => {
      // if this exists, don't do anything
      if (newComments["step_wise"][step.tool_run_id]) {
        return;
      }

      newComments["step_wise"][step.tool_run_id] = {
        description: step.description,
        tool: toolDisplayNames[step.tool_name] || "Unknown tool",
        comments: "",
        inputs: step.inputs,
        outputs: step.outputs_storage_keys,
      };
    });

    setComments(newComments);
  }, [analysisSteps]);

  return (
    <Modal
      title={<p className="text-2xl text-gray-900">What went wrong?</p>}
      open={open}
      footer={null}
      onCancel={(ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        setModalVisible(false);
      }}
      centered
      className={"w-10/12 h-11/12"}
      rootClassName="feedback-modal"
    >
      <div className="flex flex-row">
        <div className={`general-feedback py-5 pr-5 w-4/12`}>
          <p className="text-lg  text-gray-900 font-bold">General feedback</p>
          <p className="text-sm  text-gray-400">
            You can leave general comments about the overall plan here
          </p>
          <div className={`mr-4`}>
            <textarea
              className="w-full min-h-10 p-2 border border-gray-300 rounded-md"
              placeholder="Leave your feedback here..."
              disabled={loading}
              value={comments.general}
              rows={8}
              onChange={(ev) => {
                setComments({
                  ...comments,
                  general: ev.target.value,
                });
              }}
            />
          </div>
        </div>
        <div className={`step-wise-feedback py-5 pl-5 w-8/12`}>
          <p className="text-lg  text-gray-900 font-bold">Step wise feedback</p>
          <p className="text-sm  text-gray-400">
            You can leave detailed comments for specific steps here
          </p>
          <div className={`p-5 flex border transition-all rounded-md`}>
            <div className="flex flex-row my-4">
              <div className="relative">
                <StepsDag
                  steps={analysisSteps}
                  nodeSize={[40, 10]}
                  nodeGap={[30, 50]}
                  dag={dag}
                  setDag={setDag}
                  setDagLinks={setDagLinks}
                  dagLinks={dagLinks}
                  skipAddStepNode={true}
                  setActiveNode={setActiveNode}
                  activeNode={activeNode}
                  setLastOutputNodeAsActive={false}
                  // alwaysShowPopover={activeSection === "step"}
                  extraNodeClasses={(node) => {
                    return node.data.isTool
                      ? `rounded-md px-1 text-center`
                      : "";
                  }}
                  toolIcon={(node) => (
                    <p className="text-sm m-0">
                      {toolShortNames[node?.data?.step?.tool_name] ||
                        "Unknown tool"}
                    </p>
                  )}
                />
              </div>
              <div className="user-comments-ctr flex flex-col pl-8 relative flex-grow">
                {activeNode && activeNode.data.isError && (
                  <div class="absolute -top-6 flex flex-row items-center rounded-md ">
                    <div className="bg-medium-red px-2 rounded-md text-white">
                      <div class="rounded-full  bg-dark-red mr-1 w-2 h-2 inline-block"></div>
                      This step had an error
                    </div>
                  </div>
                )}

                {activeNode &&
                comments?.["step_wise"]?.[activeNode.data.step.tool_run_id] ? (
                  activeNode.data.isTool ? (
                    <div>
                      <p className="text-sm font-bold text-gray-900 ">
                        {
                          comments["step_wise"][
                            activeNode.data.step.tool_run_id
                          ].tool
                        }
                      </p>
                      <p className="text-sm text-gray-900 ">
                        {
                          comments["step_wise"][
                            activeNode.data.step.tool_run_id
                          ].description
                        }
                      </p>
                      <p
                        className="text-sm font-bold text-gray-900"
                        style={{ paddingTop: "1em" }}
                      >
                        The model generated these inputs for this step:
                      </p>
                      <p className="text-sm text-gray-900 ">
                        {Object.entries(
                          comments["step_wise"][
                            activeNode.data.step.tool_run_id
                          ].inputs
                        ).map(([key, value]) => (
                          <div key={key}>
                            <span className="italic">{key}</span>:{" "}
                            {/* {JSON.stringify(value)} */}
                            {/* if value is a number or string, display it. Else, display a JSON stringified version of it */}
                            {typeof value === "string" ||
                            typeof value === "number"
                              ? value
                              : JSON.stringify(value)}
                          </div>
                        ))}
                      </p>
                      <p
                        className="text-sm font-bold text-gray-900"
                        style={{ paddingTop: "1em" }}
                      >
                        The outputs of this step were stored in the following
                        variables:
                      </p>
                      <p className="text-sm text-gray-900 ">
                        {comments["step_wise"][
                          activeNode.data.step.tool_run_id
                        ].outputs.map((output) => (
                          <div key={output}>{output}</div>
                        ))}
                      </p>
                      <textarea
                        className="w-full min-h-10 p-2 border border-gray-300 rounded-md"
                        value={
                          comments["step_wise"][
                            activeNode.data.step.tool_run_id
                          ].comment
                        }
                        disabled={loading}
                        placeholder={`Leave your feedback about "${comments["step_wise"][activeNode.data.step.tool_run_id].tool}" here...`}
                        onChange={(ev) => {
                          const newComments = {
                            ...comments,
                          };
                          newComments["step_wise"][
                            activeNode.data.step.tool_run_id
                          ].comment = ev.target.value;

                          setComments(newComments);
                        }}
                      />
                    </div>
                  ) : (
                    <div></div>
                  )
                ) : (
                  <div className="text-gray-400">
                    Click on a node to leave a comment
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      <Button
        type="primary"
        onClick={handleSubmit}
        loading={loading}
        disabled={loading}
      >
        Submit
      </Button>
    </Modal>
  );
}
