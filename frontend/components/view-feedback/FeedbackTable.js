import { useEffect, useState, useContext } from "react";
import setupBaseUrl from "../../utils/setupBaseUrl";
import { Table, Button, Spin } from "antd";
import { MessageManagerContext } from "@defogdotai/agents-ui-components/core-ui";

const FeedbackTable = ({
  token,
  apiKeyName,
  feedbackColumns,
  feedback,
  filter,
  goldenQueries,
  setGoldenQueries,
  handleNegativeFeedback,
}) => {
  // to keep track of whether a question, query pair is golden- key: question_sql, value: bool
  const [goldenQueryMap, setGoldenQueryMap] = useState({});
  const [addingGoldenQuery, setAddingGoldenQuery] = useState(false);
  const [goldenQueryUpdated, setGoldenQueryUpdated] = useState(false);
  const message = useContext(MessageManagerContext);

  useEffect(() => {
    updateGoldenQueryMap();
  }, [goldenQueries, goldenQueryUpdated, feedback]);

  const updateGoldenQueryMap = async () => {
    const map = {};
    feedback.forEach((row) => {
      const key = `${row[2]}_${normalizeSQL(row[3])}`;
      const isGolden = (goldenQueries || []).some(
        (goldenQuery) =>
          goldenQuery.question === row[2] &&
          normalizeSQL(goldenQuery.sql) === normalizeSQL(row[3])
      );
      map[key] = isGolden;
    });
    setGoldenQueryMap(map);
  };

  const addToGoldenQueries = async (question, sqlquery) => {
    const isGolden = await checkifGoldenQuery(question, sqlquery);
    if (isGolden) {
      return;
    }

    const res = await fetch(
      setupBaseUrl("http", `integration/update_golden_queries`),
      {
        method: "POST",
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
          golden_queries: [...goldenQueries, { question, sql: sqlquery }],
        }),
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
    const data = await res.json();
    setGoldenQueries([...goldenQueries, { question, sql: sqlquery }]);
    return data;
  };

  const checkifGoldenQuery = async (question, sqlquery) => {
    const isGolden = (goldenQueries || []).some((goldenquery) => {
      const normalizedGoldenSQL = normalizeSQL(goldenquery.sql);
      const normalizedSQLQuery = normalizeSQL(sqlquery);

      const questionMatch = goldenquery.question.trim() === question.trim();
      const sqlMatch = normalizedGoldenSQL === normalizedSQLQuery;

      return questionMatch && sqlMatch;
    });

    return isGolden;
  };

  const handleAddToGoldenQueries = async (question, sqlquery) => {
    setAddingGoldenQuery(true);
    try {
      const res = await addToGoldenQueries(question, sqlquery);
      if (res.status == "success")
        message.success("Added to Golden Queries successfully!");
      await updateGoldenQueryMap();
    } catch (error) {
      console.error("Failed to add to golden queries:", error);
      message.error("Failed to add to Golden Queries.");
    } finally {
      setAddingGoldenQuery(false);
      setGoldenQueryUpdated(!goldenQueryUpdated); // Toggle the state to trigger useEffect whenever the golden queries are updated
    }
  };

  const normalizeSQL = (sql) => {
    return sql.replace(/\s+/g, " ").trim();
  };

  const toFirstCapital = (str) => {
    if (!str) return str;
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  };

  const columns = feedbackColumns.map((col, index) => {
    if (col == "created_at") {
      return {
        title: "Timestamp",
        dataIndex: col,
        key: col,
        render: (text) => (
          <div style={{ color: "grey" }}>
            {/* text is a date string in the format YYYY-MM-DD HH:MM, convert it into a format like Mar 27, HH:MM */}
            {new Date(text).toLocaleString("en-US", {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        ),
        width: "7%",
        align: "center",
      };
    }
    if (col === "feedback_type") {
      return {
        title: "Type",
        dataIndex: col,
        key: col,
        render: (text) => (
          <Button
            type="primary"
            shape="round"
            size="small"
            style={{
              backgroundColor:
                text.toLowerCase() === "bad" ? "#f5222d" : "#52c41a", // Red for bad, green for good
              borderColor: text.toLowerCase() === "bad" ? "#f5222d" : "#52c41a",
              color: "#fff",
            }}
          >
            {toFirstCapital(text)}
          </Button>
        ),
        width: "5%",
        align: "center",
      };
    }
    if (col === "query_generated") {
      return {
        title: <div style={{ textAlign: "center" }}>Generated SQL Query</div>,
        dataIndex: col,
        key: col,
        render: (text) => (
          <pre
            style={{
              whiteSpace: "pre-wrap",
              backgroundColor: "#f4f4f4",
              maxHeight: "300px",
              overflow: "auto",
            }}
          >
            {text}
          </pre>
        ),
        width: "40%",
      };
    }
    if (col === "feedback_text") {
      return {
        title: "Feedback Text",
        dataIndex: col,
        key: col,
        render: (text) => (
          <div
            style={{
              color: "#FF8C00",
              fontFamily: "Courier, monospace",
              fontSize: "1.1em",
              maxHeight: "300px",
              overflow: "auto",
            }}
          >
            {text}
          </div>
        ),
        width: "20%",
        align: "center",
      };
    }
    if (col === "question") {
      return {
        title: "Question",
        dataIndex: col,
        key: col,
        render: (text, record) => (
          <div
            style={{
              maxHeight: "300px",
              overflow: "auto",
            }}
          >
            {text}
            {record.parentQuestionText && (
              <>
                <br />
                <span style={{ color: "grey" }}>
                  Parent Question Text: {record.parentQuestionText}
                </span>
              </>
            )}
          </div>
        ),
        width: "20%",
        align: "center",
      };
    }
    return {
      title: col,
      dataIndex: col,
      key: col,
    };
  });

  columns.push({
    title: "Recommendation",
    key: "recommendation",
    render: (text, record) => {
      const isGolden =
        goldenQueryMap[
          `${record.question}_${normalizeSQL(record.query_generated)}`
        ];
      return record.feedback_type.toLowerCase() === "bad" ? (
        <Button
          onClick={() =>
            handleNegativeFeedback(
              record.question,
              record.query_generated,
              record.feedback_text
            )
          }
          style={{
            backgroundColor: "#4CAF50",
            borderColor: "#4CAF50",
            color: "#fff",
            minWidth: "95%",
          }}
        >
          Improve using Feedback
        </Button>
      ) : (
        <Button
          onClick={async () => {
            try {
              await handleAddToGoldenQueries(
                record.question,
                record.query_generated
              );
            } catch (error) {
              console.error("Failed to add to golden queries:", error);
            }
          }}
          disabled={isGolden}
          style={{
            backgroundColor: isGolden ? "#f0e68c" : "#ffd700",
            borderColor: isGolden ? "#f0e68c" : "#ffd700",
            color: "#000",
            opacity: isGolden ? 0.4 : 1,
            minWidth: "95%",
          }}
        >
          {isGolden ? "Already a Golden Query" : "Add to Golden Queries"}
        </Button>
      );
    },
    width: "8%",
    align: "center",
  });

  const filteredFeedback = feedback.filter(
    (row) =>
      row[1]?.toLowerCase().includes(filter?.toLowerCase()) ||
      row[2]?.toLowerCase().includes(filter?.toLowerCase()) ||
      row[3]?.toLowerCase().includes(filter?.toLowerCase())
  );

  const dataSource = filteredFeedback.map((row, index) => {
    const rowData = {};
    feedbackColumns.forEach((col, colIndex) => {
      rowData[col] = row[colIndex];
    });
    rowData.key = index;
    return rowData;
  });

  return (
    <Spin spinning={addingGoldenQuery} tip="Adding to Golden Queries...">
      <div className="w-full h-full p-1 bg-gray-50 shadow rounded-lg">
        <Table
          columns={columns}
          dataSource={dataSource}
          pagination={false}
          scroll={{ x: true }}
          rowKey="key"
        />
      </div>
    </Spin>
  );
};

export default FeedbackTable;
