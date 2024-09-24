import { useState, useEffect, useRef } from "react";
import Instructions from "./Instructions";
import MetadataEditor from "./EditableMetadata";
import ResultsPercentages from "./ResultsPercentages";
import { message, Modal, Button, Spin, Card, Slider, Progress } from "antd";
import {
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ArrowUpOutlined,
} from "@ant-design/icons";
import setupBaseUrl from "$utils/setupBaseUrl";

const IMGO = ({ token, apiKeyName, updateGlossary, updateMetadata }) => {
  const [modalVisible, setModalVisible] = useState(false);
  const [loadingIndex, setLoadingIndex] = useState(null);
  const [loading, setLoading] = useState(false);

  // store the logs/output of each step
  const [results, setResults] = useState({});
  // store the final recommendations
  const [recommendations, setRecommendations] = useState(null);

  const optimizedGlossaryRef = useRef(null);
  const optimizedMetadataRef = useRef(null);

  const [newGlossary, setNewGlossary] = useState("");
  const [newMetadata, setNewMetadata] = useState(null);

  const [updatingInstructions, setUpdatingInstructions] = useState(false);

  const [showScrollToTop, setShowScrollToTop] = useState(false);
  const modalContentRef = useRef(null); // Ref for modal scrollable content

  const iterations = [
    {
      title: "Use Current Metadata and Glossary",
      description:
        "Generate, validate, and correct golden queries using the current metadata and glossary. Then optimize both.",
    },
    {
      title: "Use Optimized Glossary and Current Metadata",
      description:
        "Generate, validate, and correct golden queries using the optimized glossary from the first iteration.",
    },
    {
      title: "Use Optimized Metadata and Current Glossary",
      description:
        "Generate, validate, and correct golden queries using the optimized metadata from the first iteration.",
    },
    {
      title: "Use Optimized Metadata and Optimized Glossary",
      description:
        "Generate, validate, and correct golden queries using both the optimized metadata and glossary from previous iterations.",
    },
  ];

  const steps = [
    {
      name: "Generate Golden Queries",
      endpoint: "generate_golden_queries_from_questions",
      payload: () => ({
        token,
        key_name: apiKeyName,
        max_num_queries: 4,
        db_type: "postgres",
        optimized_glossary: null,
        optimized_metadata: null,
      }),
    },
    {
      name: "Check Validity of the Generated Queries",
      endpoint: "check_generated_golden_queries_validity",
      payload: () => ({
        token,
        key_name: apiKeyName,
        db_type: "postgres",
        optimized_glossary: null,
        optimized_metadata: null,
      }),
    },
    {
      name: "Check Correctness of the Generated Queries",
      endpoint: "check_generated_golden_queries_correctness",
      payload: () => ({
        token,
        key_name: apiKeyName,
        db_type: "postgres",
        optimized_glossary: null,
        optimized_metadata: null,
      }),
    },
  ];

  const optimizationSteps = [
    {
      name: "Optimize Glossary",
      endpoint: "optimize_glossary",
      payload: () => ({
        token,
        key_name: apiKeyName,
      }),
    },
    {
      name: "Optimize Metadata",
      endpoint: "optimize_metadata",
      payload: () => ({
        token,
        key_name: apiKeyName,
      }),
    },
  ];

  // this is the final step that will be executed after all iterations- i.e. call to recommendations endpoint
  const finalStep = {
    name: "Recommendations for Glossary and Metadata",
    endpoint: "get_recommendation_for_glossary_and_metadata",
    payload: () => ({
      token,
      key_name: apiKeyName,
      db_type: "postgres",
    }),
  };

  useEffect(() => {
    console.log("Renderinng IMGO modal visible state:", modalVisible);
    if (modalVisible) {
      executeWorkflow();
    }
  }, [modalVisible]);

  const executeWorkflow = async () => {
    setLoading(true);
    try {
      for (let iteration = 0; iteration < iterations.length; iteration++) {
        const currentSteps =
          iteration === 0 ? [...steps, ...optimizationSteps] : steps;
        for (let step of currentSteps) {
          await handleApiRequest(step, iteration);
        }
      }
      // Automatically trigger recommendations after workflow steps are completed
      await handleFinalRecommendations();
    } catch (e) {
      console.error("Error during IMGO workflow:", e);
      message.error("Failed during IMGO workflow.");
    } finally {
      setLoading(false);
    }
  };

  const handleApiRequest = async (step, iteration = 0) => {
    const stepKey = `${step.name} ${iterations[iteration].title}`;
    setLoadingIndex(stepKey);
    let payload = step.payload();

    if (iteration === 1) {
      payload.optimized_glossary = optimizedGlossaryRef.current;
      setNewGlossary(optimizedGlossaryRef.current);
    } else if (iteration === 2) {
      payload.optimized_metadata = optimizedMetadataRef.current;
      setNewMetadata(optimizedMetadataRef.current);
    } else if (iteration === 3) {
      payload.optimized_glossary = optimizedGlossaryRef.current;
      setNewGlossary(optimizedGlossaryRef.current);
      payload.optimized_metadata = optimizedMetadataRef.current;
      setNewMetadata(optimizedMetadataRef.current);
    }

    try {
      const res = await fetch(setupBaseUrl("http", step.endpoint), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (step.name === "Optimize Glossary") {
        optimizedGlossaryRef.current = data.optimized_glossary;
      } else if (step.name === "Optimize Metadata") {
        optimizedMetadataRef.current = data.optimized_metadata;
      }

      const filteredData = { ...data };
      delete filteredData.task_id;

      setResults((prevResults) => ({
        ...prevResults,
        [stepKey]: filteredData,
      }));

      if (step.onSuccess) step.onSuccess(filteredData);

      const { task_id } = data;
      if (task_id) {
        const pollTaskStatus = async (taskId) => {
          console.log("starting polling now");
          let isTaskCompleted = false;
          while (!isTaskCompleted) {
            const statusRes = await fetch(
              setupBaseUrl("http", "check_task_status"),
              {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({
                  token,
                  key_name: apiKeyName,
                  task_id: taskId,
                }),
              }
            );
            const statusData = await statusRes.json();

            if (statusData.status === "completed") {
              isTaskCompleted = true;
              return isTaskCompleted;
            }
            if (statusData.status === "not_found") {
              return false;
            }
            await new Promise((resolve) => setTimeout(resolve, 10000)); // 10 seconds interval
          }
          return isTaskCompleted;
        };

        const completed = await pollTaskStatus(task_id);

        if (completed) {
          const finalData = {
            ...data,
            finalmessage: "Task completed successfully ✅",
          };
          delete finalData.task_id;

          setResults((prevResults) => ({
            ...prevResults,
            [stepKey]: finalData,
          }));

          if (step.onSuccess) step.onSuccess(finalData);
        }
      }
    } catch (e) {
      console.error(`Error executing step ${stepKey}:`, e);
      message.error(`Failed to execute step ${stepKey}.`);
    } finally {
      setLoadingIndex(null);
    }
  };

  const handleFinalRecommendations = async () => {
    try {
      const res = await fetch(setupBaseUrl("http", finalStep.endpoint), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(finalStep.payload()),
      });
      const data = await res.json();
      setRecommendations(data);
    } catch (e) {
      console.error("Error fetching final recommendations:", e);
      message.error("Failed to fetch final recommendations.");
    }
  };

  const recommendationMessage = (recommendations) => {
    console.log(recommendations);
    if (
      recommendations.is_glossary_optimization_recommended &&
      recommendations.is_metadata_optimization_recommended
    ) {
      return `Recommendations: Focus on improving both Metadata and Glossary.`;
    } else if (recommendations.is_glossary_optimization_recommended) {
      return `Recommendations: Focus on improving Glossary.`;
    } else if (recommendations.is_metadata_optimization_recommended) {
      return `Recommendations: Focus on improving Metadata.`;
    } else {
      return `We do not have any recommendations for you at this point. Please add more golden queries and check back.`;
    }
  };

  const onClose = () => {
    setModalVisible(false);
    setLoading(false);
    setResults({});
    setRecommendations(null);

    optimizedGlossaryRef.current = null;
    optimizedMetadataRef.current = null;
  };

  // Handle scroll inside the modal
  const handleScroll = () => {
    const scrollTop = modalContentRef.current?.scrollTop || 0;
    if (scrollTop > 200) {
      setShowScrollToTop(true);
    } else {
      setShowScrollToTop(false);
    }
  };

  // Scroll to top function
  const scrollToTop = () => {
    modalContentRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    if (modalContentRef.current) {
      modalContentRef.current.addEventListener("scroll", handleScroll);
    }
    return () => {
      if (modalContentRef.current) {
        modalContentRef.current.removeEventListener("scroll", handleScroll);
      }
    };
  }, [modalVisible]);

  return (
    <>
      <Button onClick={() => setModalVisible(true)} className="w-full">
        Magic Finetune
      </Button>
      <Modal
        title={
          <div className="text-2xl font-semibold text-center mt-2 mb-5">
            Recommendations for Improving Instructions and Metadata
          </div>
        }
        onCancel={onClose}
        footer={[
          <Button key="close" onClick={onClose} style={{ width: "100%" }}>
            Close
          </Button>,
        ]}
        width="80%"
        // className="max-h-full overflow-y-auto"
        open={modalVisible}
      >
        <div
          className="space-y-4"
          ref={modalContentRef}
          style={{ maxHeight: "80vh", overflowY: "auto" }}
        >
          {recommendations ? (
            <Card title="Results" className="bg-white shadow-md">
              <p className="mb-2 font-semibold">
                {recommendationMessage(recommendations)}
              </p>
              {recommendations.is_glossary_optimization_recommended && (
                <Instructions
                  title="Optimized Instructions"
                  description="These are the optimized glossary recommendations. You can edit them below before accepting changes."
                  glossary={newGlossary}
                  setGlossary={setNewGlossary}
                  updateGlossary={updateGlossary}
                  updateGlossaryLoadingFunction={setUpdatingInstructions}
                  isLoading={false}
                  isUpdatingInstructions={updatingInstructions}
                />
              )}
              {recommendations.is_metadata_optimization_recommended && (
                <MetadataEditor
                  title="Optimised Metadata"
                  description="These are the suggested descriptions for each column in the database. You can edit them below before updating the metadata."
                  metadata={newMetadata}
                  updateMetadata={updateMetadata}
                />
              )}
              {recommendations &&
                recommendations.valid_pct_list &&
                recommendations.correct_pct_list && (
                  <ResultsPercentages
                    validPctList={recommendations.valid_pct_list}
                    correctPctList={recommendations.correct_pct_list}
                    overallPctList={recommendations.overall_list}
                  />
                )}
            </Card>
          ) : (
            <Spin>
              <div className="text-center italic text-lg m-4 mb-5">
                {loading
                  ? "Please bear with us as we run multiple iterations to provide you with the best recommendations. This can take a few minutes."
                  : ""}
              </div>
            </Spin>
          )}

          {iterations.map((iteration, iterationIndex) => (
            <div
              key={iterationIndex}
              className="border border-gray-300 p-4 rounded-lg"
            >
              <h3 className="font-semibold text-lg">{iteration.title}</h3>
              <p className="text-sm text-gray-600 mb-4 mt-1">
                {iteration.description}
              </p>
              {(iterationIndex === 0
                ? [...steps, ...optimizationSteps]
                : steps
              ).map((step, stepIndex) => (
                <div
                  key={stepIndex}
                  className="rounded-lg flex flex-col"
                  style={{
                    borderBottom:
                      stepIndex < steps.length - 1
                        ? "1px solid #e0e0e0"
                        : "none",
                  }}
                >
                  <div className="flex items-center flex-1 px-3 py-2 border border-gray-300 rounded-lg shadow-sm bg-white mt-3">
                    <span
                      style={{
                        flexShrink: 0,
                        marginRight: "8px",
                        color:
                          loadingIndex === `${step.name} ${iteration.title}`
                            ? "orange"
                            : results[`${step.name} ${iteration.title}`]
                              ? "green"
                              : "red",
                      }}
                    >
                      {loadingIndex === `${step.name} ${iteration.title}` ? (
                        <Spin
                          indicator={
                            <LoadingOutlined style={{ color: "orange" }} />
                          }
                        />
                      ) : results[`${step.name} ${iteration.title}`] ? (
                        <CheckCircleOutlined />
                      ) : (
                        <CloseCircleOutlined />
                      )}
                    </span>
                    <span className="flex-1">{step.name}</span>
                  </div>

                  {results[`${step.name} ${iteration.title}`] && (
                    <div className="mt-2 bg-black text-white p-4 rounded font-mono text-sm overflow-auto max-h-96">
                      {Object.entries(
                        results[`${step.name} ${iteration.title}`]
                      )
                        .filter(([key]) => key !== "task_id")
                        .map(([key, value], idx) => (
                          <div key={idx}>
                            {typeof value === "object" ? (
                              <pre>{JSON.stringify(value, null, 2)}</pre>
                            ) : (
                              <span>{value}</span>
                            )}
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
        {/* Scroll-to-top message and arrow inside modal */}
        {showScrollToTop && (
          <div className="fixed bottom-10 right-10 flex flex-col items-center">
            {recommendations && (
              <div className="bg-gray-200 text-black p-2 mb-4 rounded shadow">
                Results are ready!
              </div>
            )}
            <div
              onClick={scrollToTop}
              className={`p-3 text-white rounded-full cursor-pointer shadow-lg transition ${
                recommendations
                  ? "bg-lime-600 hover:bg-green-400 animate-bounce"
                  : "bg-gray-800 hover:bg-gray-600"
              }`}
            >
              <ArrowUpOutlined className="text-xl" />
            </div>
          </div>
        )}
      </Modal>
    </>
  );
};

export default IMGO;
