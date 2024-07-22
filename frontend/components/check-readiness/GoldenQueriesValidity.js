import React, { useState } from "react";
import { Table, Button, Tooltip as AntTooltip } from "antd";
import {
  QuestionCircleOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip as RechartsTooltip,
  Legend,
} from "recharts";

const COLORS = ["#0088FE", "#FF8042"]; // shades of blue and orange

const GoldenQueriesValidity = ({
  loadingGoldenQueries,
  totalGoldenQueries,
  totalGoldenQueriesValid,
  totalGoldenQueriesInvalid,
  invalidGoldenQueries,
  checkGoldenQueriesValidity,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const data = [
    { name: "Valid Golden Queries", value: totalGoldenQueriesValid },
    { name: "Invalid Golden Queries", value: totalGoldenQueriesInvalid },
  ];

  const dataSource = invalidGoldenQueries.map((query, index) => ({
    key: index,
    question: `Question ${index + 1}: ${query.question}`,
    sql: query.sql,
    error: query.valid_error,
  }));

  const columns = [
    {
      title: "Question",
      dataIndex: "question",
      key: "question",
      width: "33%",
      align: "center",
    },
    {
      title: "SQL",
      dataIndex: "sql",
      key: "sql",
      width: "33%",
      align: "center",
    },
    {
      title: "Error",
      dataIndex: "error",
      key: "error",
      width: "33%",
      align: "center",
    },
  ];

  const handleClick = () => {
    if (!isVisible) checkGoldenQueriesValidity();
    setIsVisible(!isVisible);
  };

  return (
    <div style={{ padding: "1.5em", paddingBottom: "0em" }}>
      <Button
        type="primary"
        onClick={handleClick}
        loading={loadingGoldenQueries}
        ghost
        style={{ width: "100%", marginTop: "1em" }}
      >
        {isVisible
          ? "Hide Golden Queries Validity"
          : "1. Check Golden Queries Validity"}
        <AntTooltip title="See if your golden queries can be executed against an empty database with your schema!">
          <QuestionCircleOutlined
            style={{
              marginLeft: "0em",
              fontSize: "1.2em",
              color: "#1890ff",
              cursor: "pointer",
            }}
          />
        </AntTooltip>
      </Button>
      {isVisible && (
        <>
          <div
            style={{
              textAlign: "center",
              marginTop: "2em",
              marginBottom: "2em",
            }}
          >
            <p style={{ fontSize: "1.2em" }}>
              Total Golden Queries: {totalGoldenQueries}
            </p>
            <PieChart width={400} height={250} style={{ margin: "0 auto" }}>
              <Pie
                data={data}
                cx={200}
                cy={100}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Pie>
              <RechartsTooltip />
              <Legend />
            </PieChart>
          </div>

          <p style={{ fontSize: "1.2em" }}>
            <ExclamationCircleOutlined
              style={{ color: "#ff4d4f", marginRight: "0.5em" }}
            />
            The following is a list of invalid Golden queries:
          </p>

          <Table
            dataSource={dataSource}
            columns={columns}
            pagination={false}
            style={{ marginTop: "1em" }}
          />
        </>
      )}
    </div>
  );
};

export default GoldenQueriesValidity;
