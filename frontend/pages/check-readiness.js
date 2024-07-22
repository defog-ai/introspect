import React, { useEffect, useState } from "react";
import Meta from "$components/layout/Meta";
import { Row, Col, Select, Tooltip, message } from "antd";
import {
  SafetyCertificateOutlined,
  QuestionCircleOutlined,
  AuditOutlined,
} from "@ant-design/icons";
import BasicStatus from "../components/check-readiness/BasicStatus";
import GoldenQueriesValidity from "../components/check-readiness/GoldenQueriesValidity";
import InstructionConsistency from "../components/check-readiness/InstructionConsistency";
import GoldenQueryCoverage from "../components/check-readiness/GoldenQueryCoverage";

import setupBaseUrl from "$utils/setupBaseUrl";
import Scaffolding from "$components/layout/Scaffolding";
import CustomTooltip from "$components/layout/Tooltip";

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

  const apiKeyNames = (
    process.env.NEXT_PUBLIC_API_KEY_NAMES || "REPLACE_WITH_API_KEY_NAMES"
  ).split(",");
  const [apiKeyName, setApiKeyName] = useState(null);

  const checkBasicReadiness = async () => {
    let token;
    if (localStorage.getItem("defogToken")) {
      token = localStorage.getItem("defogToken");
    } else {
      message.error("Please login to continue");
      return;
    }

    setloadingBasicStatus(true);
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") + `/readiness/basic`,
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
    }
  };

  const checkGoldenQueriesValidity = async () => {
    setLoadingGoldenQueries(true);
    const res = await fetch(
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") +
        `/readiness/check_golden_queries_validity`,
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
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") +
        `/readiness/check_instruction_consistency`,
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
      (process.env.NEXT_PUBLIC_AGENTS_ENDPOINT || "") +
        `/readiness/check_golden_query_coverage`,
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
        <h1
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            paddingTop: "1em",
            paddingBottom: "0em",
          }}
        >
          <SafetyCertificateOutlined
            style={{ marginRight: "0.5em", fontSize: "3em", color: "#52c41a" }}
          />
        </h1>
        <h1
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            paddingTop: "0.5em",
            paddingBottom: "1em",
          }}
        >
          System Readiness Check
          <Tooltip title="Check if you have added aligned your Defog instance sufficiently">
            <QuestionCircleOutlined
              style={{
                marginLeft: "0.5em",
                fontSize: "1em",
                color: "#1890ff",
                cursor: "pointer",
              }}
            />
          </Tooltip>
        </h1>
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
            <h2 style={{ display: "flex", alignItems: "center" }}>
              <Tooltip title="Do regular quality checks to keep defog fully customised for databse">
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
