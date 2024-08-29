import { useState, useEffect } from "react";
import Meta from "../components/layout/Meta";
import Scaffolding from "../components/layout/Scaffolding";
import setupBaseUrl from "$utils/setupBaseUrl";
import { Row, Col, Select, Input, Spin } from "antd";
import FeedbackTable from "../components/view-feedback/FeedbackTable";
import RecommendationsModal from "../components/view-feedback/RecommendationsModal";
import { HistoryOutlined } from "@ant-design/icons";

const ViewFeedback = () => {
  const apiKeyNames = (
    process.env.NEXT_PUBLIC_API_KEY_NAMES || "Your Database"
  ).split(",");
  const [apiKeyName, setApiKeyName] = useState(null);
  const [token, setToken] = useState();

  // feedback data
  const [feedbackColumns, setFeedbackColumns] = useState([]);
  const [feedback, setFeedback] = useState([]);

  // golden queries
  const [goldenQueries, setGoldenQueries] = useState([]);

  // information about the row that the user clicked on for improve using feedback
  const [question, setQuestion] = useState("");
  const [sqlGenerated, setSqlGenerated] = useState("");
  const [userFeedback, setUserFeedback] = useState("");

  const [isModalVisible, setIsModalVisible] = useState(false); // recommendations modal
  const [filter, setFilter] = useState(""); // filter for search

  // loading state for the feedback data
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const apiKeyName = localStorage.getItem("defogDbSelected");
    const token = localStorage.getItem("defogToken");
    if (apiKeyName) {
      setApiKeyName(apiKeyName);
    } else {
      setApiKeyName(apiKeyNames[0]);
    }
    setToken(token);
  }, []);

  useEffect(() => {
    //
    if (apiKeyName) {
      localStorage.setItem("defogDbSelected", apiKeyName);
    }
    getFeedback(token, apiKeyName);
    getGoldenQueries();
  }, [token, apiKeyName]);

  // fetches data about all the past feedbacks given by the user
  const getFeedback = async (token, apiKeyName) => {
    setLoading(true);
    if (!token) {
      return;
    }
    const res = await fetch(setupBaseUrl("http", `get_feedback`), {
      method: "POST",
      body: JSON.stringify({
        token: token,
        key_name: apiKeyName,
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });
    const data = await res.json();
    setFeedbackColumns(data.columns);
    setFeedback(data.data);
    setLoading(false);
  };

  const fetchDynamicGlossary = async (question, token, apiKeyName) => {
    const res = await fetch(
      setupBaseUrl("http", `integration/get_dynamic_glossary`),
      {
        method: "POST",
        body: JSON.stringify({
          question: question,
          token: token,
          key_name: apiKeyName,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
    const data = await res.json();
    return data;
  };

  const getCurrentGlossary = async (question) => {
    if (!token || !apiKeyName) {
      return;
    }
    const dets = await fetchDynamicGlossary(question, token, apiKeyName);
    const glossary = dets["pruned_glossary"];
    return glossary;
  };

  const fetchGoldenQueries = async (token, apiKeyName) => {
    const res = await fetch(
      setupBaseUrl("http", `integration/get_glossary_golden_queries`),
      {
        method: "POST",
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
    const data = await res.json();
    return data["golden_queries"];
  };

  const getGoldenQueries = async () => {
    if (!token || !apiKeyName) {
      return;
    }
    const { goldenQueries } = await fetchGoldenQueries(token, apiKeyName);
    setGoldenQueries(goldenQueries);
  };

  const handleNegativeFeedback = async (question, sqlQuery, userFeedback) => {
    setQuestion(question);
    setSqlGenerated(sqlQuery);
    setUserFeedback(userFeedback);
    setIsModalVisible(true);
  };

  return (
    <div className="flex justify-center">
      <Meta />
      <Scaffolding id={"view-feedback"} userType={"admin"}>
        {apiKeyNames.length > 1 ? (
          <Row type={"flex"} height={"100vh"}>
            <Col span={24} style={{ paddingBottom: "1em" }}>
              <Select
                style={{ width: "100%" }}
                onChange={(e) => {
                  setApiKeyName(e);
                }}
                options={apiKeyNames.map((item) => {
                  return { value: item, key: item, label: item };
                })}
                value={apiKeyName}
              />
            </Col>
          </Row>
        ) : null}
        <div className="w-full">
          {/* create a filter for the users to type in */}
          <div className="flex justify-center items-center flex-col m-3">
            <h1>
              <HistoryOutlined style={{ fontSize: "3em", color: "#1890ff" }} />{" "}
            </h1>
            <h1 className="text-2xl mt-4">Feedback History</h1>
          </div>

          <Row className="flex justify-center mb-4">
            <Col span={24}>
              <Input
                placeholder="Filter rows by text"
                onChange={(e) => {
                  setFilter(e.target.value);
                }}
                className="w-full p-3 rounded-lg border border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 transition duration-200"
              />
            </Col>
          </Row>
          <Spin spinning={loading} tip="Loading past feedback data...">
            <FeedbackTable
              token={token}
              apiKeyName={apiKeyName}
              feedbackColumns={feedbackColumns}
              feedback={feedback}
              filter={filter}
              goldenQueries={goldenQueries}
              setGoldenQueries={setGoldenQueries}
              handleNegativeFeedback={handleNegativeFeedback}
            />
          </Spin>

          {isModalVisible && (
            <RecommendationsModal
              isModalVisible={isModalVisible}
              setIsModalVisible={setIsModalVisible}
              token={token}
              apiKeyName={apiKeyName}
              question={question}
              sqlGenerated={sqlGenerated}
              userFeedback={userFeedback}
              getCurrentGlossary={getCurrentGlossary}
            />
          )}
        </div>
      </Scaffolding>
    </div>
  );
};

export default ViewFeedback;
