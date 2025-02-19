import { useState, useEffect } from "react";
import {
  Input,
  Button,
  SpinningLoader,
  Table
} from "@defogdotai/agents-ui-components/core-ui";
import { Edit, Trash2, Save } from "lucide-react";
import LineBlock from "../layout/LineBlock";
import AddQueryModal from "./AddQueryModal";

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
    // Reset editing rows whenever goldenQueries changes length
    setEditingRows({});
  }, [goldenQueries.length]);

  // Modal for adding a new question/SQL
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [newQuestion, setNewQuestion] = useState("");
  const [newSql, setNewSql] = useState("");

  const toggleEditMode = (uniqueKey) => {
    setEditingRows((prev) => ({ ...prev, [uniqueKey]: !prev[uniqueKey] }));
  };

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
    setIsModalVisible(false);
  };

  /**
   * 1) Define columns.
   *
   * We pass a `render` function that references `record.__origIndex`
   * to update the correct row in state, rather than using the render-time index.
   */
  const columns = [
    {
      title: "Question",
      dataIndex: "question",
      key: "question",
      width: "30%",
      render: (cellValue, record) => {
        const isEditing = editingRows[record.__origIndex];
        if (isEditing) {
          return (
            <Input
              value={cellValue}
              onChange={(e) => {
                const value = e.target.value;
                setGoldenQueries((prev) => {
                  // Update the correct index in the array
                  const newQueries = [...prev];
                  newQueries[record.__origIndex].question = value;
                  return newQueries;
                });
              }}
              disabled={isLoading || isUpdatingGoldenQueries}
              inputClassNames="min-h-[2.5rem] resize-y"
            />
          );
        }
        // Non-editing mode
        return (
          <LineBlock
            helperText=""
            mainText={cellValue}
            onUpdate={() => {}}
            isEditable={false}
          />
        );
      },
    },
    {
      title: "SQL Query",
      dataIndex: "sql",
      key: "sql",
      width: "55%",
      render: (cellValue, record) => {
        const isEditing = editingRows[record.__origIndex];
        if (isEditing) {
          return (
            <Input
              value={cellValue}
              onChange={(e) => {
                const value = e.target.value;
                setGoldenQueries((prev) => {
                  const newQueries = [...prev];
                  newQueries[record.__origIndex].sql = value;
                  return newQueries;
                });
              }}
              disabled={isLoading || isUpdatingGoldenQueries}
              inputClassNames="font-mono text-sm min-h-[6rem] resize-y bg-gray-50 dark:bg-dark-bg-secondary border border-gray-300 dark:border-dark-border dark:text-dark-text-primary"
            />
          );
        }
        // Non-editing mode
        return (
          <pre className="whitespace-pre-wrap bg-gray-100 dark:bg-dark-bg-secondary dark:text-dark-text-primary max-h-72 overflow-auto px-2 py-1">
            {cellValue}
          </pre>
        );
      },
    },
    {
      title: "Actions",
      dataIndex: "__actions", // not a real data field
      key: "actions",
      width: "15%",
      render: (_, record) => {
        const isEditing = editingRows[record.__origIndex];
        return (
          <div className="flex items-center gap-2 justify-center">
            <Button
              variant={isEditing ? "primary" : "normal"}
              icon={isEditing ? <Save /> : <Edit />}
              onClick={() => {
                if (isEditing) {
                  // When saving, call your update API
                  updateGoldenQueries(record.question, record.sql);
                }
                toggleEditMode(record.__origIndex);
              }}
              disabled={isLoading || isUpdatingGoldenQueries}
            />
            <Button
              variant="danger"
              icon={<Trash2 />}
              onClick={() => {
                deleteGoldenQueries(record.question);
              }}
              disabled={isLoading || isUpdatingGoldenQueries}
            />
          </div>
        );
      },
    },
  ];

  /**
   * 2) Transform goldenQueries into rows for the Table:
   *    - Provide a stable key (like __origIndex) to track the row in state
   *    - 'key' is used by React, while __origIndex is used for editing logic
   */
  const tableRows = goldenQueries.map((query, i) => ({
    ...query,
    key: `row-${i}`,
    __origIndex: i,
  }));

  /**
   * 3) rowCellRender
   *    Our Table component uses a single 'rowCellRender' function
   *    to actually build <td>. We check if there's a 'render' in the column definition.
   */
  const rowCellRender = ({
    cellValue,
    row,
    dataIndex,
    column,
  }) => {
    // If this column has a custom render function, call it
    if (typeof column.render === "function") {
      return (
        <td
          key={row.key + "-" + dataIndex}
          className="px-3 py-2 align-top text-sm text-gray-700 dark:text-gray-200"
        >
          {column.render(cellValue, row)}
        </td>
      );
    }
    // Fallback: default cell
    return (
      <td
        key={row.key + "-" + dataIndex}
        className="px-3 py-2 align-top text-sm text-gray-700 dark:text-gray-200"
      >
        {cellValue}
      </td>
    );
  };

  return (
    <div className="w-full p-4 mb-4">
      <h2 className="text-xl mb-3 font-semibold">Golden Queries</h2>
      <p className="mb-6 text-gray-700">
        The golden queries are SQL queries used as examples by the model to
        learn about how your database is structured. You can see and edit them
        below.
      </p>

      {/* Loading/Updating overlay */}
      <div className="relative">
        {(isLoading || isUpdatingGoldenQueries) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/70 dark:bg-gray-900/70 backdrop-blur-[1px] z-10">
            <SpinningLoader classNames="text-blue-500 h-6 w-6" />
            <span className="mt-2 text-gray-600 dark:text-gray-300">
              {isUpdatingGoldenQueries
                ? "Updating Golden Queries..."
                : "Loading Golden Queries"}
            </span>
          </div>
        )}

        {/* 4) Render our custom table */}
        <Table
          columns={columns}
          rows={tableRows}
          rowCellRender={rowCellRender}
          rootClassNames="max-h-screen overflow-auto"
          // no pagination or show all rows
          pagination={{
            defaultPageSize: tableRows.length,
            showSizeChanger: false,
          }}
          paginationPosition="bottom"
          showSearch={false}
        />
      </div>

      <Button
        variant="primary"
        className="mt-4 px-4 py-2 min-w-[200px]"
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
        />
      )}
    </div>
  );
};

export default GoldenQueries;
