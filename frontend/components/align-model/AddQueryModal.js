import { useState } from "react";
import { Modal, Input, Spin } from "antd";
import { StarFilled } from "@ant-design/icons";
import LineBlock from "$components/layout/LineBlock";
import DisplayData from "$components/view-feedback/DisplayDataFrame";

const AddQueryModal = ({
  handleOk,
  handleCancel,
  newQuestion,
  setNewQuestion,
  newSql,
  setNewSql,
  newColumns,
  newData,
  generateSqlQuery,
}) => {
  const [loading, setLoading] = useState(false);

  // generates a new SQL query based on the new question
  const onUpdate = async (newQuestion) => {
    setLoading(true);
    setNewQuestion(newQuestion);
    setNewSql("Generating SQL...");
    const query = await generateSqlQuery(newQuestion);
    setNewSql(query);
    setLoading(false);
  };

  return (
    <Modal
      title={
        <div className="flex flex-col justify-center items-center text-xl mb-4">
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
          className="min-h-52 font-mono text-sm p-2 bg-gray-50 border border-gray-300"
        />
      </Spin>

      {/* display results of the query*/}
      {newSql && newSql !== "Generating SQL..." && (
        <div className="mt-5 ">
          <DisplayData columns={newColumns} data={newData} />
        </div>
      )}
    </Modal>
  );
};

export default AddQueryModal;
