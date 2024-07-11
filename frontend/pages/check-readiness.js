import React, { useEffect, useState } from "react";
import Meta from "$components/layout/Meta";
import { Row, Col, Space, Button, message } from "antd";
import setupBaseUrl from "$utils/setupBaseUrl";
import Scaffolding from "$components/layout/Scaffolding";
import CustomTooltip from "$components/layout/Tooltip";

const CheckReadiness = () => {
  const [loading, setLoading] = useState(false);
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
  const checkBasicReadiness = async () => {
    let token;
    if (localStorage.getItem("defogToken")) {
      token = localStorage.getItem("defogToken");
    } else {
      message.error("Please login to continue");
      return;
    }

    setLoading(true);
    const res = await fetch(setupBaseUrl("http", `readiness/basic`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        token: token,
      }),
    });
    const data = await res.json();
    if (data.success) {
      setLoading(false);
      setMetadataUploaded(data.metadata);
      setGoldenQueriesUploaded(data.golden_queries);
      setGlossaryUploaded(data.glossary);
    } else {
      setLoading(false);
      message.error(
        "An error occurred while checking if your metadata was adequately added."
      );
    }
  };

  const checkGoldenQueriesValidity = async () => {
    setLoading(true);
    const res = await fetch(
      setupBaseUrl("http", `readiness/check_golden_queries_validity`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
        }),
      }
    );
    const data = await res.json();
    setLoading(false);
    setTotalGoldenQueries(data.total_golden_queries);
    setTotalGoldenQueriesInvalid(data.invalid_golden_queries_count);
    setTotalGoldenQueriesValid(
      data.total_golden_queries - data.invalid_golden_queries_count
    );
    setInvalidGoldenQueries([...data.invalid_golden_queries]);
    console.log(data);
  };

  const checkInstructionConsistency = async () => {
    setLoading(true);
    const res = await fetch(
      setupBaseUrl("http", `readiness/check_instruction_consistency`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
        }),
      }
    );
    const data = await res.json();
    setInstructionConsistencyRating(data.message);
    setInconsistentInstructions([...data.inconsistent_glossary_lines]);
    setInconsistentReason([...data.reasons_for_inconsistency]);
    setLoading(false);
    console.log(data);
  };

  const checkGoldenQueryCoverage = async () => {
    setLoading(true);
    const res = await fetch(
      setupBaseUrl("http", `readiness/check_golden_query_coverage`),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
        }),
      }
    );
    const data = await res.json();
    setTotalTables(data.num_total_tables);
    setTotalColumns(data.num_total_cols);
    setCoveredTables(data.num_total_tables - data.num_missing_tables);
    setCoveredColumns(data.num_total_cols - data.num_missing_cols);
    setMissingTables([...data.missing_tables]);
    setLoading(false);
    console.log(data);
  };

  useEffect(() => {
    const token = localStorage.getItem("defogToken");
    setToken(token);
    setLoading(true);
    setTimeout(() => {
      checkBasicReadiness();
    }, 100);
  }, []);

  return (
    <>
      <Meta />
      <Scaffolding id={"check-readiness"} userType={"admin"}>
        <h1>Check readiness</h1>
        <p>Check if you have added aligned your Defog instance sufficiently</p>
        <Row
          gutter={{
            xs: 8,
            sm: 16,
            md: 24,
            lg: 32,
          }}
        >
          <Col span={24} style={{ paddingTop: "1em" }}>
            <h2>The Basics</h2>
            <ul>
              <li>
                <CustomTooltip
                  tooltipText={
                    "Metadata (table names, columns names, column descriptions) updated on Defog?"
                  }
                  mainText={"Metadata Updated:"}
                />{" "}
                <Space /> {loading ? "⏳" : metadataUploaded ? "✅" : "❌"}
              </li>
              <li>
                <CustomTooltip
                  tooltipText={
                    "Explicit instructions to guide generation added to Defog?"
                  }
                  mainText={"Instruction Set Updated:"}
                />{" "}
                <Space /> {loading ? "⏳" : glossaryUploaded ? "✅" : "❌"}
              </li>
              <li>
                <CustomTooltip
                  tooltipText={
                    "Golden queries to ground the model's generation added to Defog?"
                  }
                  mainText={"Golden Queries Updated:"}
                />{" "}
                <Space /> {loading ? "⏳" : goldenQueriesUploaded ? "✅" : "❌"}
              </li>
            </ul>
          </Col>

          <Col span={24} style={{ paddingTop: "1em" }}>
            <h2>Quality Checks</h2>

            <h3>Check Golden Queries Validity</h3>
            <p>
              See if your golden queires can be executed against an empty
              database with your schema
            </p>
            <Button
              type="primary"
              onClick={() => {
                checkGoldenQueriesValidity();
              }}
              loading={loading}
              ghost
            >
              Check Golden Queries
            </Button>
            <p>Total Golden Queries: {totalGoldenQueries}</p>
            <p>Valid Golden Queries: {totalGoldenQueriesValid}</p>
            <p>Invalid Golden Queries: {totalGoldenQueriesInvalid}</p>
            <p>The following is a list of invalid golden queries:</p>
            {/* invalidGoldenQueries is an array of objects in the form {'question': ..., 'query': ..., 'valid_error': ...} */}
            {/* render each of those */}
            <p style={{ paddingTop: "1em" }}>
              {invalidGoldenQueries.map((query, index) => (
                <>
                  <p>
                    Question {index + 1}: {query.question}
                  </p>
                  <p>SQL</p>
                  <pre>{query.sql}</pre>
                  <p>Error</p>
                  <pre>{query.valid_error}</pre>
                </>
              ))}
            </p>

            <h3>Check Instruction Consistency</h3>
            <p>
              See if your instructions are consistent and do not contradict each
              other
            </p>
            <Button
              type="primary"
              onClick={() => {
                checkInstructionConsistency();
              }}
              loading={loading}
              ghost
            >
              Check Instructions Consistency
            </Button>
            <p>{instructionConsistencyRating}</p>
            {instructionConsistencyRating &&
            instructionConsistencyRating.indexOf("Excellent") === -1 ? (
              <>
                <p>Inconsistent Instructions:</p>
                <ul>
                  {inconsistentInstructions.map((instruction, index) => (
                    <li key={"inconsistent-instruction" + index}>
                      {instruction}
                    </li>
                  ))}
                </ul>
                <p>Reasons for inconsistency:</p>
                <ul>
                  {inconsistentReason.map((reason, index) => (
                    <li key={"inconsistent-reason-" + index}>{reason}</li>
                  ))}
                </ul>
              </>
            ) : null}

            <h3>Check Golden Query Coverage</h3>
            <p>
              See if your golden queries cover a significant portion of your
              schema
            </p>
            <Button
              type="primary"
              onClick={() => {
                checkGoldenQueryCoverage();
              }}
              loading={loading}
              ghost
            >
              Check Golden Query Coverage
            </Button>
            <p>
              {coveredTables} out of {totalTables} tables in your database are
              mentioned in golden queries.
            </p>
            <p>
              {coveredColumns} out of {totalColumns} total columns in your
              database are mentioned in golden queries.
            </p>
            <p>The following tables are missing from the golden queries:</p>
            <ul>
              {missingTables.map((table, index) => (
                <li key={"missing-table-" + index}>{table}</li>
              ))}
            </ul>
          </Col>
        </Row>
      </Scaffolding>
    </>
  );
};

export default CheckReadiness;
