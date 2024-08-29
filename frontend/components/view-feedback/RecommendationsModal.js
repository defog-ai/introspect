import { useState, useEffect } from "react";
import setupBaseUrl from "../../utils/setupBaseUrl";
import { useRouter } from "next/router";
import DisplayDataFrame from "./DisplayDataFrame";
import DisplayQuery from "./DisplayQuery";
import { Button, Modal, Spin, Input } from "antd";
import LineBlock from "../layout/LineBlock";
const { TextArea } = Input;
import {
  BulbOutlined,
  SyncOutlined,
  PlayCircleOutlined,
  PlusCircleOutlined,
  StarOutlined,
  MessageOutlined,
  QuestionCircleOutlined,
} from "@ant-design/icons";

const RecommendationsModal = ({
  isModalVisible,
  setIsModalVisible,
  token,
  apiKeyName,
  question,
  sqlGenerated,
  userFeedback,
  getCurrentGlossary,
}) => {
  const router = useRouter();

  const [currentQuestion, setCurrentQuestion] = useState(question);
  const [currentFeedback, setCurrentFeedback] = useState(userFeedback);
  const [recommendedInstructions, setRecommendedInstructions] = useState("");

  const [updatedQuery, setUpdatedQuery] = useState("");
  const [updatedColumns, setUpdatedColumns] = useState([]);
  const [updatedData, setUpdatedData] = useState([]);

  const [populatingInstructions, setPopulatingInstructions] = useState(true); // generating intelligent recommendations
  const [isRunning, setIsRunning] = useState(false); // running defog with updated instructions
  const [permanentlyUpdatedGlossary, setPermanentlyUpdatedGlossary] =
    useState(false); // permanently added instructions into glossary

  useEffect(() => {
    populateInstructions();
  }, [currentFeedback]);

  const closeModal = () => {
    setRecommendedInstructions("");
    setUpdatedQuery("");
    setUpdatedData([]);
    setUpdatedColumns([]);
    setIsModalVisible(false);
  };

  const populateInstructions = async () => {
    setPopulatingInstructions(true);

    try {
      const response = await fetch(
        setupBaseUrl("http", `get_instructions_recommendation`),
        {
          method: "POST",
          body: JSON.stringify({
            token: token,
            key_name: apiKeyName,
            question: currentQuestion,
            sql_generated: sqlGenerated,
            user_feedback: currentFeedback,
          }),
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error, status = ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        // Check for any error message in the response body
        throw new Error(data.error);
      }

      setRecommendedInstructions(data["instruction_set"] || "");
    } catch (error) {
      console.error("Failed to populate instructions:", error.message);
      setRecommendedInstructions(
        "Failed to load instructions due to an error."
      );
    } finally {
      setPopulatingInstructions(false);
    }
  };

  const appendToGlossary = async (newGlossary) => {
    const res = await fetch(
      setupBaseUrl("http", `integration/update_glossary`),
      {
        method: "POST",
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
          new_instructions: newGlossary,
          append: true,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
    const data = await res.json();
    return data;
  };

  const reRunWithUpdatedInstructions = async () => {
    setIsRunning(true);
    const currentGlossary = await getCurrentGlossary(currentQuestion);
    console.log(currentGlossary);

    let updatedGlossary;

    // momentarily, add the recommendedInstructions to the glossary
    try {
      updatedGlossary = currentGlossary + "\n" + recommendedInstructions;
    } catch (error) {
      console.error(
        "Failed to append instructions to glossary:",
        error.message
      );
    }

    // run query for the question with the updated glossary
    const res = await fetch(setupBaseUrl("http", `query`), {
      method: "POST",
      body: JSON.stringify({
        token: token,
        key_name: apiKeyName,
        question: currentQuestion,
        previous_context: [],
        dev: false,
        ignore_cache: true,
        glossary: updatedGlossary,
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });
    const data = await res.json();

    // revert the glossary back to the original state
    setUpdatedQuery(data["query_generated"]);
    setUpdatedColumns(data["columns"]);
    setUpdatedData(data["data"]);
    setIsRunning(false);
    console.log(data);
  };

  const permanentlyAddInstructions = async () => {
    appendToGlossary(recommendedInstructions);
    setRecommendedInstructions("");
    setPermanentlyUpdatedGlossary(true);
  };

  return (
    <Modal
      title=""
      open={isModalVisible}
      onOk={closeModal}
      onCancel={closeModal}
      width={"80vw"}
    >
      <>
        <div>
          <h2
            style={{
              textAlign: "center",
              marginTop: "1em",
              marginBottom: "1em",
            }}
          >
            <div>
              <BulbOutlined className="text-4xl" />
              <p className="text-2xl mt-4">Recommendations</p>
            </div>
          </h2>
          <LineBlock
            helperText={
              <>
                <MessageOutlined
                  style={{ fontSize: "16px", color: "##FFFAF0" }}
                />
                &nbsp; Your Feedback:
              </>
            }
            mainText={userFeedback}
            onUpdate={(text) => {
              setCurrentFeedback(text);
            }}
            isEditable={!populatingInstructions}
          />
          <p style={{ paddingLeft: "1.1em", fontSize: "1.1em" }}>
            {!populatingInstructions
              ? "Based on your feedback these are the instructions when given to the model might help get the right answer. Feel free to edit before hitting ask defog again:"
              : "The more meaningful the feedback, the better suggestions you get! You will soon have an option to edit the feedback and doing so automatically regenerates new instructions for you!"}
          </p>

          {populatingInstructions ? (
            <Spin tip="Aligning the model based on your feedback. This might take up to 30-60 seconds. We appreciate your patience!">
              <TextArea
                disabled={true}
                placeholder="Generating instructions..."
                style={{ width: "95%", padding: "1em", margin: "1em" }}
              />
            </Spin>
          ) : (
            <TextArea
              value={recommendedInstructions}
              onChange={(e) => {
                setRecommendedInstructions(e.target.value);
              }}
              placeholder="Instructions Appear Here"
              style={{
                width: "95%",
                padding: "1em",
                margin: "1em",
                minHeight: "150px",
              }}
            />
          )}
        </div>
        <LineBlock
          helperText={
            <>
              <QuestionCircleOutlined
                style={{ fontSize: "16px", color: "##FFFAF0" }}
              />
              &nbsp; Question:
            </>
          }
          mainText={question}
          onUpdate={(text) => setCurrentQuestion(text)}
          isEditable={!populatingInstructions && !isRunning}
        />
        <div>
          <Button
            onClick={reRunWithUpdatedInstructions}
            // type="primary"
            type="dashed"
            style={{
              minWidth: "23%",
              padding: "1.2em",
              paddingBottom: "1.1em",
              margin: "1em",
              marginBottom: "0.5em",
              marginTop: "0.5em",
              height: "auto",
            }}
            disabled={
              recommendedInstructions === "" ||
              populatingInstructions ||
              isRunning
            }
          >
            <PlayCircleOutlined
              style={{ fontSize: "20px", marginRight: "8px" }}
            />
            {isRunning ? "Running..." : "Ask Defog with Updated Instructions"}
          </Button>
        </div>
        {!populatingInstructions && updatedQuery && (
          <>
            <div
              style={{
                width: "95%",
                paddingLeft: "1.1em",
                marginBottom: "2em",
              }}
            >
              <h2
                className="text-xl mt-4 mb-3"
                style={{
                  textAlign: "left",
                }}
              >
                {" "}
                <SyncOutlined
                  style={{ fontSize: "24px", marginRight: "8px" }}
                />{" "}
                Updated Results Using Instructions
              </h2>
              <h3 className="text-lg mt-2 mb-1 text-left">
                Generated SQL Query
              </h3>
              <DisplayQuery query={updatedQuery} />
              <h3 className="text-lg mt-2 mb-1 text-left">Query Results</h3>
              <DisplayDataFrame
                columns={updatedColumns}
                data={(updatedData || []).map((row) => row.map((cell) => cell))}
              />
            </div>
            <div>
              <LineBlock
                helperText={
                  <StarOutlined
                    style={{ fontSize: "16px", color: "##FFFAF0" }}
                  />
                }
                mainText="Did this improve your results? If yes, consider adding those instructions to the glossary permanently to tailor it for the future."
                onUpdate={() => {}}
                isEditable={false}
              />

              <Button
                onClick={permanentlyAddInstructions}
                // type="primary"
                type="dashed"
                style={{
                  minWidth: "23%",
                  padding: "1.2em",
                  paddingBottom: "1.2em",
                  margin: "1em",
                  marginBottom: "0.5em",
                  marginTop: "0.5em",
                  height: "auto",
                }}
              >
                <PlusCircleOutlined
                  style={{ fontSize: "20px", marginRight: "8px" }}
                />
                Add Recommendations to Glossary
              </Button>
              {permanentlyUpdatedGlossary && (
                <p style={{ paddingLeft: "1em", marginTop: "1em" }}>
                  Instructions have been added to {""}
                  <span
                    style={{
                      cursor: "pointer",
                      color: "#1890ff",
                      textDecoration: "underline",
                      fontWeight: "bold",
                    }}
                    onClick={() => router.push("/align-model")}
                  >
                    glossary
                  </span>{" "}
                  successfully.
                </p>
              )}
            </div>
          </>
        )}
      </>
    </Modal>
  );
};

export default RecommendationsModal;
