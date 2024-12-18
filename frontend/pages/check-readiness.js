import { useEffect, useState, useContext } from "react";
import Meta from "$components/layout/Meta";
import { Row, Col, Select, Tooltip, Table, Spin } from "antd";
import {
  SafetyCertificateOutlined,
  AuditOutlined,
  ApartmentOutlined,
} from "@ant-design/icons";
import BasicStatus from "$components/check-readiness/BasicStatus";
import GoldenQueriesValidity from "$components/check-readiness/GoldenQueriesValidity";
import InstructionConsistency from "$components/check-readiness/InstructionConsistency";
import GoldenQueryCoverage from "$components/check-readiness/GoldenQueryCoverage";

import CodeMirror, { EditorView } from "@uiw/react-codemirror";
import { sql as codemirrorSql } from "@codemirror/lang-sql";

import setupBaseUrl from "$utils/setupBaseUrl";
import Scaffolding from "$components/layout/Scaffolding";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";

const CheckReadiness = () => {
  // Loading states for each check
  const [loadingBasicStatus, setloadingBasicStatus] = useState(false);
  const [loadingGoldenQueries, setLoadingGoldenQueries] = useState(false);
  const [loadingInstructionConsistency, setLoadingInstructionConsistency] =
    useState(false);
  const [loadingGoldenQueryCoverage, setLoadingGoldenQueryCoverage] =
    useState(false);

  const [token, setToken] = useState("");

  // Basic readiness
  const [metadataUploaded, setMetadataUploaded] = useState(false);
  const [goldenQueriesUploaded, setGoldenQueriesUploaded] = useState(false);
  const [glossaryUploaded, setGlossaryUploaded] = useState(false);

  // Golden queries validity
  const [totalGoldenQueries, setTotalGoldenQueries] = useState(0);
  const [totalGoldenQueriesValid, setTotalGoldenQueriesValid] = useState(0);
  const [totalGoldenQueriesInvalid, setTotalGoldenQueriesInvalid] = useState(0);
  const [invalidGoldenQueries, setInvalidGoldenQueries] = useState([]);

  // Instruction consistency
  const [instructionConsistencyRating, setInstructionConsistencyRating] =
    useState("");
  const [inconsistentInstructions, setInconsistentInstructions] = useState([]);
  const [inconsistentReason, setInconsistentReason] = useState([]);

  // Golden query coverage
  const [totalTables, setTotalTables] = useState(0);
  const [totalColumns, setTotalColumns] = useState(0);
  const [coveredTables, setCoveredTables] = useState(0);
  const [coveredColumns, setCoveredColumns] = useState(0);
  const [missingTables, setMissingTables] = useState([]);

  // regression results
  const [regressionLoading, setRegressionLoading] = useState(false);
  const [totalRegressionQueries, setTotalRegressionQueries] = useState(0);
  const [totalRegressionQueriesValid, setTotalRegressionQueriesValid] =
    useState(0);
  const [regressionQueries, setRegressionQueries] = useState([]);
  const [regressionStartFrom, setRegressionStartFrom] = useState(0);
  const [regressionResultsRemaining, setRegressionResultsRemaining] =
    useState(null);

  const [apiKeyNames, setApiKeyNames] = useState([]);

  const getApiKeyNames = async (token) => {
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + "/get_api_key_names",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
        }),
      }
    );
    if (!res.ok) {
      throw new Error(
        "Failed to get api key names - are you sure your network is working?"
      );
    }
    const data = await res.json();
    setApiKeyNames(data.api_key_names);
    setApiKeyName(data.api_key_names[0]);
  };
  const [apiKeyName, setApiKeyName] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    getApiKeyNames(token);
  }, []);

  const checkBasicReadiness = async () => {
    let token;
    if (localStorage.getItem("defogToken")) {
      token = localStorage.getItem("defogToken");
    } else {
      message.error("Please login to continue");
      return;
    }

    setloadingBasicStatus(true);
    const res = await fetch(setupBaseUrl("http", `readiness/basic`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token: token,
        key_name: apiKeyName,
      }),
    });
    const data = await res.json();
    if (data.success) {
      setloadingBasicStatus(false);
      setMetadataUploaded(data.metadata);
      setGoldenQueriesUploaded(data.golden_queries);
      setGlossaryUploaded(data.glossary);
    } else {
      setloadingBasicStatus(false);
      message.error(
        "An error occurred while checking if your metadata was adequately added."
      );
      console.log(data);
    }
  };

  const checkGoldenQueriesValidity = async () => {
    setLoadingGoldenQueries(true);
    const res = await fetch(
      setupBaseUrl("http", `readiness/check_golden_queries_validity`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
        }),
      }
    );
    const data = await res.json();
    setLoadingGoldenQueries(false);
    setTotalGoldenQueries(data.total_golden_queries);
    setTotalGoldenQueriesInvalid(data.invalid_golden_queries_count);
    setTotalGoldenQueriesValid(
      data.total_golden_queries - data.invalid_golden_queries_count
    );
    setInvalidGoldenQueries([...data.invalid_golden_queries]);
    console.log(data);
  };

  const checkInstructionConsistency = async () => {
    setLoadingInstructionConsistency(true);
    const res = await fetch(
      setupBaseUrl("http", `readiness/check_instruction_consistency`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
        }),
      }
    );
    const data = await res.json();
    setInstructionConsistencyRating(data.message);
    setInconsistentInstructions([...data.inconsistent_glossary_lines]);
    setInconsistentReason([...data.reasons_for_inconsistency]);
    setLoadingInstructionConsistency(false);
    console.log(data);
  };

  const checkGoldenQueryCoverage = async () => {
    setLoadingGoldenQueryCoverage(true);
    const res = await fetch(
      setupBaseUrl("http", `readiness/check_golden_query_coverage`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
        }),
      }
    );
    const data = await res.json();
    setTotalTables(data.num_total_tables);
    setTotalColumns(data.num_total_cols);
    setCoveredTables(data.num_total_tables - data.num_missing_tables);
    setCoveredColumns(data.num_total_cols - data.num_missing_cols);
    setMissingTables([...data.missing_tables]);
    setLoadingGoldenQueryCoverage(false);
    console.log(data);
  };

  const getRegressionResults = async () => {
    setRegressionLoading(true);
    const res = await fetch(
      setupBaseUrl("http", `readiness/regression_results`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
          start_from: regressionStartFrom,
        }),
      }
    );
    const data = await res.json();
    setTotalRegressionQueries(data.total);
    setTotalRegressionQueriesValid(data.correct);
    setRegressionQueries([...data.regression_queries]);
    setRegressionStartFrom((prev) => prev + 5);
    setRegressionResultsRemaining(data.results_remaining);
    setRegressionLoading(false);
  };

  useEffect(() => {
    const apiKeyName = localStorage.getItem("defogDbSelected");
    if (apiKeyName) {
      setApiKeyName(apiKeyName);
    } else {
      setApiKeyName(apiKeyNames[0]);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    if (!apiKeyName) {
      return;
    }
    if (apiKeyName) {
      localStorage.setItem("defogDbSelected", apiKeyName);
    }
    setToken(token);
    setloadingBasicStatus(true);
    setTimeout(() => {
      checkBasicReadiness();
    }, 100);
  }, [apiKeyName]);

  const message = useContext(MessageManagerContext);

  return (
    <>
      <Meta />
      <Scaffolding id={"check-readiness"} userType={"admin"}>
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

        <div className="flex justify-center items-center flex-col p-1 mt-1">
          <h1>
            <SafetyCertificateOutlined className="text-4xl text-blue-600" />{" "}
          </h1>
          <h1 className="text-2xl mt-4">System Readiness Check</h1>
          <p className="m-4">
            Check if you have added aligned your Defog instance sufficiently.
            These checks help ensure that Defog can provide accurate results.
          </p>
        </div>

        <div className="flex justify-center items-center flex-col p-1 mt-1">
          <h1>
            <ApartmentOutlined className="text-4xl text-blue-600" />{" "}
          </h1>
          <h1 className="text-2xl mt-4">Test for Regressions</h1>
          <p className="m-4">
            Check if Defog's performance might have regressed on golden queries
            and/or questions that it previously performed well on.
          </p>
          <button
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            onClick={getRegressionResults}
            disabled={regressionLoading}
          >
            {totalRegressionQueries === 0
              ? "Test first 5 queries for regressions"
              : "Test next 5 queries for regressions"}
          </button>

          {regressionLoading ? (
            <>
              Loading, the regression test can take up to 2 minutes... <Spin />
            </>
          ) : totalRegressionQueries > 0 ? (
            <div className="flex justify-center items-center flex-col p-1 mt-1">
              <p className="m-4">
                Of the {totalRegressionQueries} queries that you just tested,
                Defog got{" "}
                {totalRegressionQueries === totalRegressionQueriesValid
                  ? "all"
                  : ""}{" "}
                {totalRegressionQueriesValid} out of {totalRegressionQueries}{" "}
                exactly right. Please review the queries below to see which ones
                were not exactly right - some of them might be close enough to
                be acceptable.
              </p>

              <h1 className="text-2xl mt-4">Queries</h1>
              <Table
                dataSource={regressionQueries}
                columns={[
                  {
                    title: "Question",
                    dataIndex: "question",
                    key: "question",
                  },
                  {
                    title: "Golden SQL",
                    dataIndex: "sql_golden",
                    key: "sql_golden",
                    render: (text) => {
                      return (
                        <CodeMirror
                          extensions={[
                            codemirrorSql(),
                            EditorView.lineWrapping,
                          ]}
                          value={text}
                          basicSetup={{
                            lineNumbers: false,
                          }}
                          editable={false}
                        />
                      );
                    },
                  },
                  {
                    title: "Generated SQL",
                    dataIndex: "sql_gen",
                    key: "sql_gen",
                    render: (text) => {
                      return (
                        <CodeMirror
                          extensions={[
                            codemirrorSql(),
                            EditorView.lineWrapping,
                          ]}
                          value={text}
                          basicSetup={{
                            lineNumbers: false,
                          }}
                          editable={false}
                        />
                      );
                    },
                  },
                  {
                    title: "Correct",
                    dataIndex: "correct",
                    key: "correct",
                    render: (text) => {
                      return text ? (
                        <span className="bg-green p-2">Yes</span>
                      ) : (
                        <span className="bg-red p-2">No</span>
                      );
                    },
                  },
                ]}
              />
            </div>
          ) : (
            <p className="my-2">
              Press the button above to test for regressions. If you have not
              added any golden queries or given any feedback, this test will not
              run.
            </p>
          )}
        </div>

        <Row
          gutter={{
            xs: 8,
            sm: 16,
            md: 24,
            lg: 32,
          }}
        >
          <BasicStatus
            loading={loadingBasicStatus}
            metadataUploaded={metadataUploaded}
            glossaryUploaded={glossaryUploaded}
            goldenQueriesUploaded={goldenQueriesUploaded}
          />

          <Col span={24} style={{ paddingTop: "1em" }}>
            <h2
              style={{ display: "flex", alignItems: "center" }}
              className="text-lg font-semibold"
            >
              <Tooltip title="Do regular quality checks to keep defog fully customised for your database">
                <AuditOutlined
                  style={{
                    marginRight: "0.5em",
                    fontSize: "1.2em",
                    color: "#1890ff",
                    cursor: "pointer",
                  }}
                />
              </Tooltip>
              Quality Checks
            </h2>

            <GoldenQueriesValidity
              loadingGoldenQueries={loadingGoldenQueries}
              totalGoldenQueries={totalGoldenQueries}
              totalGoldenQueriesValid={totalGoldenQueriesValid}
              totalGoldenQueriesInvalid={totalGoldenQueriesInvalid}
              invalidGoldenQueries={invalidGoldenQueries}
              checkGoldenQueriesValidity={checkGoldenQueriesValidity}
            />

            <InstructionConsistency
              loadingInstructionConsistency={loadingInstructionConsistency}
              instructionConsistencyRating={instructionConsistencyRating}
              inconsistentInstructions={inconsistentInstructions}
              inconsistentReason={inconsistentReason}
              checkInstructionConsistency={checkInstructionConsistency}
            />

            <GoldenQueryCoverage
              loadingGoldenQueryCoverage={loadingGoldenQueryCoverage}
              totalTables={totalTables}
              totalColumns={totalColumns}
              coveredTables={coveredTables}
              coveredColumns={coveredColumns}
              missingTables={missingTables}
              checkGoldenQueryCoverage={checkGoldenQueryCoverage}
            />
          </Col>
        </Row>
      </Scaffolding>
    </>
  );
};

export default CheckReadiness;
