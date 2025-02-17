import { useState, useEffect } from "react";
import { Table, Input, Button, Space, Spin } from "antd";
import { EditOutlined, DeleteOutlined, SaveOutlined } from "@ant-design/icons";
import LineBlock from "../layout/LineBlock";
import AddQueryModal from "./AddQueryModal";
import setupBaseUrl from "$utils/setupBaseUrl";

const GoldenQueries = ({
  token,
  apiKeyName,
  goldenQueries,
  setGoldenQueries,
  isLoading,
  updateGoldenQueries,
  deleteGoldenQueries,
  isUpdatingGoldenQueries,
}) => {
  const [editingRows, setEditingRows] = useState({});
  useEffect(() => {
    setEditingRows({});
  }, [goldenQueries.length]);

  // add new question and query modal state
  const [isModalVisible, setIsModalVisible] = useState(false);

  // states for the new question and query
  const [newQuestion, setNewQuestion] = useState("");
  const [newSql, setNewSql] = useState("");
  // states for the results from running the new query
  const [newColumns, setNewColumns] = useState([]);
  const [newData, setNewData] = useState([]);

  const toggleEditMode = (key) => {
    setEditingRows(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // handles submission of new question and query under modal
  const handleOk = (question, sql) => {
    if (question && sql) {
      updateGoldenQueries(question, sql);
      handleCancel();
      setGoldenQueries((prev) => [...prev, { question, sql }]);
    }
  };

  const handleCancel = () => {
    setNewQuestion("");
    setNewSql("");
    setNewColumns([]);
    setNewData([]);
    setIsModalVisible(false);
  };

  const columns = [
    {
      title: "Question",
      dataIndex: "question",
      key: "question",
      width: "30%",

      render: (text, record, index) =>
        editingRows[record.question] ? (
          <Input.TextArea
            value={text}
            onChange={(e) => {
              const value = e.target.value;
              setGoldenQueries(prev => {
                const newQueries = [...prev];
                newQueries[index].question = value;
                return newQueries;
              });
            }}
            rows={1}
            disabled={isLoading || isUpdatingGoldenQueries}
          />
        ) : (
          <LineBlock
            helperText=""
            mainText={text}
            onUpdate={() => {}}
            isEditable={false}
          />
        ),
    },
    {
      title: "SQL Query",
      dataIndex: "sql",
      key: "sql",
      width: "65%",
      render: (text, record, index) =>
        editingRows[record.question] ? (
          <Input.TextArea
            value={text}
            onChange={(e) => {
              const value = e.target.value;
              setGoldenQueries(prev => {
                const newQueries = [...prev];
                newQueries[index].sql = value;
                return newQueries;
              });
            }}
            rows={4}
            disabled={isLoading || isUpdatingGoldenQueries}
            className="font-mono text-sm p-2 bg-gray-50 dark:bg-dark-bg-secondary border border-gray-300 dark:border-dark-border dark:text-dark-text-primary"
          />
        ) : (
          <pre className="whitespace-pre-wrap bg-gray-100 dark:bg-dark-bg-secondary dark:text-dark-text-primary max-h-72 overflow-auto">
            {text}
          </pre>
        ),
    },
    {
      title: "Actions",
      key: "actions",
      width: "5%",
      align: "center",
      render: (text, record, index) => (
        <Space>
          <Button
            icon={
              editingRows[record.question] ? <SaveOutlined /> : <EditOutlined />
            }
            onClick={() => {
              console.log("CLicked!")
              if (editingRows[record.question]) {
                // If we're saving (i.e. exiting edit mode), trigger the update
                console.log("Saving!");
                updateGoldenQueries(record.question, record.sql);
              }
              toggleEditMode(record.question);
            }}
            disabled={isLoading || isUpdatingGoldenQueries}
          />
          <Button
            icon={<DeleteOutlined />}
            type="primary"
            danger
            onClick={() => {
              console.log("Clicked delete!")
              deleteGoldenQueries(record.question)
            }}
            disabled={isLoading || isUpdatingGoldenQueries}
          />
        </Space>
      ),
    },
  ];
  // Generate and execute SQL query given a question
  const generateAndExecuteQuery = async (question) => {
    try {
      const response = await fetch(setupBaseUrl("http", `query`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
          key_name: apiKeyName,
          question: question,
          previous_context: [],
          dev_body: false,
          ignore_cache: true,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch data from server");
      }

      const data = await response.json();

      setNewColumns(data.columns || []);
      setNewData(data.data || []);
      return data.query_generated || "";
    } catch (error) {
      console.error("Error generating and executing query:", error);
      return "";
    }
  };

  return (
    <div className="w-full p-4 mb-4">
      <h2 className="text-xl mb-3 font-semibold">Golden Queries</h2>
      <p className="mb-6 text-gray-700">
        The golden queries are SQL queries used as examples by the model to
        learn about how your database is structured. You can see and edit them
        below.
      </p>
      <Spin
        spinning={isLoading || isUpdatingGoldenQueries}
        tip={
          isUpdatingGoldenQueries
            ? "Updating Golden Queries..."
            : "Loading Golden Queries"
        }
      >
        <div className="max-h-screen overflow-auto">
          <Table
            columns={columns}
            dataSource={goldenQueries.map((query, index) => ({
              ...query,
              key: query.question,
            }))}
            pagination={false}
          />
        </div>
      </Spin>

      <Button
        type="primary"
        className="mt-4 h-auto p-2 min-w-56"
        onClick={() => setIsModalVisible(true)}
        disabled={isLoading || isUpdatingGoldenQueries}
      >
        Add new Question and Query
      </Button>
      {isModalVisible && (
        <AddQueryModal
          handleOk={() => handleOk(newQuestion, newSql)}
          handleCancel={handleCancel}
          newQuestion={newQuestion}
          setNewQuestion={setNewQuestion}
          newSql={newSql}
          setNewSql={setNewSql}
          newColumns={newColumns}
          newData={newData}
          generateSqlQuery={generateAndExecuteQuery}
        />
      )}
    </div>
  );
};

export default GoldenQueries;
