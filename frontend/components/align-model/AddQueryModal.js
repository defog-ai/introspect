import { useState, useEffect } from "react";
import {
  Modal,
  Input,
  SpinningLoader,
  Button,
} from "@defogdotai/agents-ui-components/core-ui";
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
  const onUpdate = (questionValue) => {
    setNewQuestion(questionValue);
    setShouldGenerateSQL(true);
  };

  // Generate SQL whenever question changes
  useEffect(() => {
    if (shouldGenerateSQL && newQuestion) {
      const fetchSQL = async () => {
        setLoading(true);
        setNewSql("Generating SQL...");
        try {
          const query = await generateSqlQuery(newQuestion);
          setNewSql(query);
        } catch (err) {
          setNewSql("// Error generating SQL");
        } finally {
          setLoading(false);
          setShouldGenerateSQL(false);
        }
      };
      fetchSQL();
    }
  }, [shouldGenerateSQL, newQuestion, generateSqlQuery, setNewSql]);

  return (
    <Modal
      open={true}
      onCancel={handleCancel}
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={handleCancel}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleOk}>
            Ok
          </Button>
        </div>
      }
      title={
        <div className="flex flex-col justify-center items-center text-xl mb-4 dark:text-dark-text-primary">
          <StarFilled
            className="text-yellow-500 mb-4 font-bold"
            style={{ fontSize: "3em" }}
          />
          <h1>Add Golden Query</h1>
        </div>
      }
      contentClassNames="w-full max-w-3xl"
    >
      <LineBlock
        helperText="Question: "
        mainText={newQuestion}
        onUpdate={onUpdate}
        isEditable={true}
        inputModeOn={true}
      />


      <div className="relative mt-4">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 z-10">
            <SpinningLoader classNames="text-blue-500 h-6 w-6" />
            <span className="ml-2 text-sm text-gray-600 dark:text-gray-300">
              Give us a few seconds...
            </span>
          </div>
        )}

        <Input
          textArea
          placeholder="SQL Query"
          value={newSql}
          onChange={(e) => setNewSql(e.target.value)}
          inputClassNames="font-mono text-sm p-2 bg-gray-50 dark:bg-dark-bg-secondary border border-gray-300 dark:border-dark-border dark:text-dark-text-primary min-h-[8rem] w-full"
          disabled={loading}
        />
      </div>
    </Modal>
  );
};

export default AddQueryModal;
