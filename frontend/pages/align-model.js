import React, { useState, useEffect } from "react";
import Meta from "$components/layout/Meta";
import { Row, Col, Switch, Input, Select, Button, message } from "antd";
import setupBaseUrl from "$utils/setupBaseUrl";
import Scaffolding from "$components/layout/Scaffolding";

const AlignModel = () => {
  const [devMode, setDevMode] = useState(false);
  const [glossary, setGlossary] = useState("");
  const [goldenQueries, setGoldenQueries] = useState([]); // [ { question: "", sql: "" }, ... ]
  const [token, setToken] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [hoverIndex, setHoverIndex] = useState(-1);
  const apiKeyNames = (
    process.env.NEXT_PUBLIC_API_KEY_NAMES || "REPLACE_WITH_API_KEY_NAMES"
  ).split(",");
  const [apiKeyName, setApiKeyName] = useState(apiKeyNames[0]);

  useEffect(() => {
    // get token
    const token = localStorage.getItem("defogToken");
    setToken(token);

    // after 100ms, get the glossary and golden queries
    getGlossaryGoldenQueries(devMode);
  }, [devMode, apiKeyName]);

  const getGlossaryGoldenQueries = async (dev) => {
    setIsLoading(true);
    const token = localStorage.getItem("defogToken");
    console.log("Right now, devMode is", dev);
    try {
      const res = await fetch(
        setupBaseUrl("http", `integration/get_glossary_golden_queries`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token,
            dev: dev,
            key_name: apiKeyName,
          }),
        }
      );
      const data = await res.json();
      setGlossary(data.glossary);
      setGoldenQueries(data.golden_queries);
      setIsLoading(false);
    } catch (e) {
      console.error(e);
      setIsLoading(false);
      message.error(
        "Failed to get instructions. Are you sure you have updated your database credentials?"
      );
    }
  };

  const updateGlossary = async () => {
    setIsLoading(true);
    const res = await fetch(
      setupBaseUrl("http", `integration/update_glossary`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          glossary,
          token,
          dev: devMode,
          key_name: apiKeyName,
        }),
      }
    );
    const data = await res.json();
    setIsLoading(false);
  };

  const updateGoldenQueries = async () => {
    setIsLoading(true);
    const res = await fetch(
      setupBaseUrl("http", `integration/update_golden_queries`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
          golden_queries: goldenQueries,
          dev: devMode,
          key_name: apiKeyName,
        }),
      }
    );
    const data = await res.json();
    setIsLoading(false);
  };

  return (
    <>
      <Meta />
      <Scaffolding id={"align-model"} userType={"admin"}>
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
                defaultValue={apiKeyName}
              />
            </Col>
          </Row>
        ) : null}
        <div style={{ paddingBottom: "1em" }}>
          <h1>Align Model</h1>
          <p>
            Here, you can see the instructions and golden queries that the model
            is currently using to create SQL queries. You can change them here,
            and also get suggestions on how to improve them.
          </p>
        </div>

        <Row type={"flex"} height={"100vh"} gutter={16}>
          <Col span={24} style={{ paddingBottom: "1em" }}>
            <Switch
              checkedChildren="Production"
              unCheckedChildren="Development"
              checked={!devMode}
              onChange={(e) => {
                setDevMode(!e);
                getGlossaryGoldenQueries(!e);
              }}
            />
          </Col>
          <Col span={6}>
            <h2>Instructions</h2>
            <p style={{ paddingBottom: "1em" }}>
              These instructions are used by the model as a guide for the SQL
              queries that it generates. You can change them below.
            </p>
            <Input.TextArea
              value={glossary}
              onChange={(e) => {
                setGlossary(e.target.value);
              }}
              autoSize={{ minRows: 8 }}
              disabled={isLoading}
            />
            <Button
              type="primary"
              style={{ marginTop: "1em" }}
              ghost
              onClick={updateGlossary}
              loading={isLoading}
              disabled={isLoading}
            >
              Update instructions on server
            </Button>
          </Col>
          <Col span={18}>
            <h2>Golden Queries</h2>
            <p style={{ paddingBottom: "1em" }}>
              The golden queries are SQL queries used as examples by the model
              to learn about how your database is structured. You can see and
              edit them below.
              <br />
              <br />
            </p>

            <Row
              type={"flex"}
              justify={"end"}
              style={{ paddingBottom: "1em" }}
              gutter={16}
            >
              {goldenQueries.map((query, i) => (
                <>
                  <Col
                    span={8}
                    style={{ paddingBottom: "1em" }}
                    onMouseEnter={() => {
                      setHoverIndex(i);
                    }}
                    onMouseLeave={() => {
                      setHoverIndex(-1);
                    }}
                  >
                    {/* create a floating button for deleting this question and query */}
                    <Button
                      type="primary"
                      danger
                      style={{
                        position: "absolute",
                        left: "0",
                        bottom: "0",
                        display: hoverIndex == i ? "block" : "none",
                      }}
                      onClick={() => {
                        const newGoldenQueries = goldenQueries.slice();
                        newGoldenQueries.splice(i, 1);
                        setGoldenQueries(newGoldenQueries);
                      }}
                      disabled={isLoading}
                      loading={isLoading}
                    >
                      Delete
                    </Button>

                    <h3>Question {i + 1}</h3>
                    <Input.TextArea
                      value={query.question}
                      onChange={(e) => {
                        // if goldenQueries is not empty, then we can change the question
                        const newGoldenQueries = goldenQueries.slice();
                        newGoldenQueries[i].question = e.target.value;
                        setGoldenQueries(newGoldenQueries);
                      }}
                      autoSize={{ minRows: 1 }}
                      disabled={isLoading}
                    />
                  </Col>
                  <Col span={16} style={{ paddingBottom: "1em" }}>
                    <h3>SQL Query {i + 1}</h3>
                    <Input.TextArea
                      value={query.sql}
                      onChange={(e) => {
                        const newGoldenQueries = goldenQueries.slice();
                        newGoldenQueries[i].sql = e.target.value;
                        setGoldenQueries(newGoldenQueries);
                      }}
                      autoSize={{ minRows: 4, maxRows: 8 }}
                      disabled={isLoading}
                    />
                  </Col>
                </>
              ))}
              {/* add a button to optionally let users create new question and queries */}
              <Col span={24}>
                <Button
                  type="primary"
                  style={{ marginTop: "1em" }}
                  ghost
                  onClick={() => {
                    const newGoldenQueries = goldenQueries.slice();
                    newGoldenQueries.push({ question: "", sql: "" });
                    setGoldenQueries(newGoldenQueries);
                  }}
                  loading={isLoading}
                  disabled={isLoading}
                >
                  Add new question and query
                </Button>
              </Col>

              <Col span={24}>
                <Button
                  type="primary"
                  style={{ marginTop: "1em" }}
                  ghost
                  onClick={updateGoldenQueries}
                  loading={isLoading}
                  disabled={isLoading}
                >
                  Update golden queries on server
                </Button>
              </Col>
            </Row>
          </Col>
        </Row>
      </Scaffolding>
    </>
  );
};

export default AlignModel;
