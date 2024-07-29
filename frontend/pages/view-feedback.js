import { useState, useEffect } from "react";
import Meta from "../components/layout/Meta";
import Scaffolding from "../components/layout/Scaffolding";
import setupBaseUrl from "$utils/setupBaseUrl";
import { Row, Col, Select, Input } from "antd";
import FeedbackTable from "../components/view-feedback/FeedbackTable";
import RecommendationsModal from "../components/view-feedback/RecommendationsModal";

const ViewFeedback = () => {
  const apiKeyNames = (
    process.env.NEXT_PUBLIC_API_KEY_NAMES || "REPLACE_WITH_API_KEY_NAMES"
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
  };

  const fetchCurrentGlossaryAndGoldenQueries = async (token, apiKeyName) => {
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
    return {
      glossary: data["glossary"] || "",
      goldenQueries: data["golden_queries"] || "",
    };
  };

  const getCurrentGlossary = async () => {
    if (!token || !apiKeyName) {
      return;
    }
    const { glossary } = await fetchCurrentGlossaryAndGoldenQueries(
      token,
      apiKeyName
    );
    return glossary;
  };

  const getGoldenQueries = async () => {
    if (!token || !apiKeyName) {
      return;
    }
    const { goldenQueries } = await fetchCurrentGlossaryAndGoldenQueries(
      token,
      apiKeyName
    );
    setGoldenQueries(goldenQueries);
  };

  const handleNegativeFeedback = async (question, sqlQuery, userFeedback) => {
    setQuestion(question);
    setSqlGenerated(sqlQuery);
    setUserFeedback(userFeedback);
    setIsModalVisible(true);
  };

  return (
    <>
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

        {/* create a filter for the users to type in */}
        <Row type={"flex"}>
          <Col span={24} style={{ paddingBottom: "1em" }}>
            <Input
              placeholder="Filter rows by text"
              onChange={(e) => {
                setFilter(e.target.value);
              }}
            />
          </Col>
        </Row>

        <FeedbackTable
          token={token}
          apiKeyName={apiKeyName}
          feedbackColumns={feedbackColumns}
          feedback={feedback}
          filter={filter}
          goldenQueries={goldenQueries}
          setGoldenQueries={setGoldenQueries}
          handleNegativeFeedback={handleNegativeFeedback}
          getFeedback={getFeedback}
        />

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
      </Scaffolding>
    </>
  );
};

export default ViewFeedback;
