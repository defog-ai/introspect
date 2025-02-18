import { useState, useEffect } from "react";
import { Modal, Input, Spin } from "antd";
import { StarFilled } from "@ant-design/icons";
import LineBlock from "$components/layout/LineBlock";

const AddQueryModal = ({
  handleOk,
  handleCancel,
  newQuestion,
  setNewQuestion,
  newSql,
  setNewSql,
  generateSqlQuery,
}) => {
  const [loading, setLoading] = useState(false);

  // Track if we need to generate SQL for a new question
  const [shouldGenerateSQL, setShouldGenerateSQL] = useState(false);

  // Handle question updates
  const onUpdate = (newQuestion) => {
    setNewQuestion(newQuestion);
    setShouldGenerateSQL(true);
  };

  // Generate SQL when question changes
  useEffect(() => {
    if (shouldGenerateSQL && newQuestion) {
      const generateSQL = async () => {
        setLoading(true);
        setNewSql("Generating SQL...");
        const query = await generateSqlQuery(newQuestion);
        setNewSql(query);
        setLoading(false);
        setShouldGenerateSQL(false);
      };
      generateSQL();
    }
  }, [shouldGenerateSQL, newQuestion, generateSqlQuery]);

  return (
    <Modal
      title={
        <div className="flex flex-col justify-center items-center text-xl mb-4 dark:text-dark-text-primary">
          <StarFilled
            className="text-yellow-500 mb-4 font-bold"
            style={{ fontSize: "3em" }}
          />
          <h1> Add Golden Query </h1>
        </div>
      }
      onOk={handleOk}
      onCancel={handleCancel}
      open={true}
      className="w-3/4"
    >
      <LineBlock
        helperText="Question: "
        mainText={newQuestion}
        onUpdate={onUpdate}
        isEditable={true}
        inputModeOn={true}
      />
      <Spin spinning={loading} tip="Give us a few seconds..">
        <Input.TextArea
          placeholder="SQL Query"
          value={newSql}
          onChange={(e) => setNewSql(e.target.value)}
          rows={4}
          className="min-h-52 font-mono text-sm p-2 bg-gray-50 dark:bg-dark-bg-secondary border border-gray-300 dark:border-dark-border dark:text-dark-text-primary"
        />
      </Spin>
    </Modal>
  );
};

export default AddQueryModal;
