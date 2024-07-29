import { useEffect, useState } from "react";
import setupBaseUrl from "../../utils/setupBaseUrl";
import { Row, Col, Button, Spin, message } from "antd";

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

    (goldenQueries || []).push({ question, sql: sqlquery });

    const res = await fetch(
      setupBaseUrl("http", `integration/update_golden_queries`),
      {
        method: "POST",
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
          golden_queries: goldenQueries,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
    const data = await res.json();
    setGoldenQueries(goldenQueries);
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

  return (
    feedbackColumns.length > 0 && (
      <Row type={"flex"} height={"100vh"}>
        <Col span={24}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              borderSpacing: 0,
              backgroundColor: "#fff",
            }}
          >
            <thead>
              <tr>
                {feedbackColumns.map((col, i) => (
                  <th
                    key={i}
                    style={{
                      textAlign: "left",
                      padding: "8px 16px",
                      borderBottom: "1px solid #e0e0e0",
                      backgroundColor: "#f0f0f0",
                      color: "#333",
                      maxWidth: col === "query_generated" ? "400px" : "200px",
                    }}
                  >
                    {col}
                  </th>
                ))}
                <th
                  key={feedbackColumns.length}
                  style={{
                    padding: "8px 16px",
                    borderBottom: "1px solid #e0e0e0",
                    backgroundColor: "#f0f0f0",
                    color: "#333",
                    textAlign: "left",
                  }}
                >
                  Recommendation
                </th>
              </tr>
            </thead>
            <tbody
              style={{
                borderCollapse: "collapse",
                borderSpacing: 0,
              }}
            >
              {feedback
                .filter(
                  (row) =>
                    row[1]?.toLowerCase().includes(filter?.toLowerCase()) ||
                    row[2]?.toLowerCase().includes(filter?.toLowerCase()) ||
                    row[3]?.toLowerCase().includes(filter?.toLowerCase())
                )
                .map((row, i) => (
                  <tr key={i}>
                    {feedbackColumns.map((col, j) => {
                      if (col === "query_generated") {
                        return (
                          <td
                            key={j}
                            style={{
                              maxWidth:
                                col === "query_generated" ? "400px" : "200px",
                              padding: "8px 16px",
                              borderBottom: "1px solid #e0e0e0",
                            }}
                          >
                            <pre style={{ whiteSpace: "pre-wrap" }}>
                              {row[j]}
                            </pre>
                          </td>
                        );
                      } else if (col === "feedback_text") {
                        return (
                          <td
                            key={j}
                            style={{
                              maxWidth: "300px",
                            }}
                          >
                            {row[j]}
                          </td>
                        );
                      } else if (col === "question") {
                        return (
                          <td key={j} style={{ maxWidth: 200 }}>
                            {row[j]}
                            {row[5] && (
                              <>
                                <br />
                                <span style={{ color: "grey" }}>
                                  Parent Question Text: {row[5]}
                                </span>
                              </>
                            )}
                          </td>
                        );
                      } else {
                        return <td key={j}>{row[j]}</td>;
                      }
                    })}
                    <td
                      key={feedbackColumns.length}
                      style={{
                        textAlign: "center",
                      }}
                    >
                      {row[1].toLowerCase() === "bad" ? (
                        <Button
                          onClick={() =>
                            handleNegativeFeedback(row[2], row[3], row[4])
                          }
                          style={{
                            backgroundColor: "#4CAF50",
                            borderColor: "#4CAF50",
                            color: "#fff",
                          }}
                        >
                          Improve using Feedback
                        </Button>
                      ) : addingGoldenQuery ? (
                        <Spin tip="Updating Golden Queries...">
                          {" "}
                          Please give us a second
                        </Spin>
                      ) : (
                        <Button
                          onClick={async () => {
                            try {
                              await handleAddToGoldenQueries(row[2], row[3]);
                            } catch (error) {
                              console.error(
                                "Failed to add to golden queries:",
                                error
                              );
                            }
                          }}
                          disabled={
                            goldenQueryMap[`${row[2]}_${normalizeSQL(row[3])}`]
                          }
                          style={{
                            backgroundColor: goldenQueryMap[
                              `${row[2]}_${normalizeSQL(row[3])}`
                            ]
                              ? "#f0e68c"
                              : "#ffd700",
                            borderColor: goldenQueryMap[
                              `${row[2]}_${normalizeSQL(row[3])}`
                            ]
                              ? "#f0e68c"
                              : "#ffd700",
                            color: "#000",
                            opacity: goldenQueryMap[
                              `${row[2]}_${normalizeSQL(row[3])}`
                            ]
                              ? 0.5
                              : 1,
                          }}
                        >
                          {goldenQueryMap[`${row[2]}_${normalizeSQL(row[3])}`]
                            ? "Already a Golden Query"
                            : "Add to Golden Queries"}
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </Col>
      </Row>
    )
  );
};

export default FeedbackTable;
