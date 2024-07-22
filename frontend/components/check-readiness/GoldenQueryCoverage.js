import React, { useState } from "react";
import { Button, Progress, Table, List, Tooltip } from "antd";
import { QuestionCircleOutlined, MinusCircleOutlined } from "@ant-design/icons";

const GoldenQueryCoverage = ({
  loadingGoldenQueryCoverage,
  totalTables,
  totalColumns,
  coveredTables,
  coveredColumns,
  missingTables,
  checkGoldenQueryCoverage,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const formatPercentage = (value) => {
    return Number(value).toPrecision(3);
  };

  const tableCoveragePercent = formatPercentage(
    (coveredTables / totalTables) * 100
  );
  const columnCoveragePercent = formatPercentage(
    (coveredColumns / totalColumns) * 100
  );

  const getProgressColor = (percent) => {
    if (percent < 10) {
      return "#ff4d4f"; // Red
    } else if (percent < 50) {
      return "#faad14"; // Orange
    } else if (percent < 80) {
      return "#a0d911"; // Light Green
    } else {
      return "#52c41a"; // Green
    }
  };

  const coverageData = [
    {
      key: "1",
      category: "Tables",
      total: totalTables,
      covered: coveredTables,
      percentage: tableCoveragePercent,
    },
    {
      key: "2",
      category: "Columns",
      total: totalColumns,
      covered: coveredColumns,
      percentage: columnCoveragePercent,
    },
  ];

  const coverageColumns = [
    {
      title: "Category",
      dataIndex: "category",
      key: "category",
      width: "16.67%",
    },
    {
      title: "Total",
      dataIndex: "total",
      key: "total",
      width: "16.67%",
    },
    {
      title: "Mentioned ",
      dataIndex: "covered",
      key: "covered",
      width: "16.67%",
    },
    {
      title: "Coverage",
      dataIndex: "percentage",
      key: "percentage",
      width: "50%",
      render: (text) => (
        <div style={{ display: "flex", alignItems: "center" }}>
          <Progress
            percent={text}
            status="active"
            strokeColor={getProgressColor(Number(text))}
            style={{ flexGrow: 1, marginRight: "10px" }}
          />
        </div>
      ),
    },
  ];

  const handleClick = () => {
    if (!isVisible) checkGoldenQueryCoverage();
    setIsVisible(!isVisible);
  };

  return (
    <div
      style={{ padding: "1.5em", paddingBottom: "0em", marginBottom: "4rem" }}
    >
      <Button
        type="primary"
        onClick={handleClick}
        loading={loadingGoldenQueryCoverage}
        ghost
        style={{ width: "100%" }}
      >
        {isVisible
          ? "Hide Golden Query Coverage"
          : "3. Check Golden Query Coverage"}
        <Tooltip title="See if your golden queries cover a significant portion of your schema and which tables are missing">
          <QuestionCircleOutlined
            style={{
              marginLeft: "0em",
              fontSize: "1.2em",
              color: "#1890ff",
              cursor: "pointer",
            }}
          />
        </Tooltip>
      </Button>

      {isVisible && (
        <>
          <div style={{ marginTop: "4em" }}>
            <Table
              dataSource={coverageData}
              columns={coverageColumns}
              pagination={false}
              style={{ marginBottom: "1em" }}
            />
          </div>

          <div
            style={{
              marginTop: "1em",
              marginBottom: "3em",
              width: "100%",
              maxHeight: "200px",
              overflowY: "auto",
            }}
          >
            <p
              style={{
                marginTop: "1em",
                marginBottom: "1em",
                fontSize: "1.2em",
              }}
            >
              <MinusCircleOutlined
                style={{ color: "#ff4d4f", marginRight: "0.3em" }}
              />
              The following tables are missing from the Golden queries:
            </p>
            <List
              dataSource={missingTables}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    title={<div style={{ textAlign: "center" }}>{item}</div>}
                  />
                </List.Item>
              )}
              bordered
            />
          </div>
        </>
      )}
    </div>
  );
};

export default GoldenQueryCoverage;
