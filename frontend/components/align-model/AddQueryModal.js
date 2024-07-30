import { Modal, Input } from "antd";
import { StarFilled } from "@ant-design/icons";
import LineBlock from "$components/layout/LineBlock";

const AddQueryModal = ({
  handleOk,
  handleCancel,
  newQuestion,
  setNewQuestion,
  newSql,
  setNewSql,
}) => {
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
      className="w-1/2"
    >
      <LineBlock
        helperText="Question: "
        mainText={newQuestion}
        onUpdate={setNewQuestion}
        isEditable={true}
        inputModeOn={true}
      />
      <Input.TextArea
        placeholder="SQL Query"
        value={newSql}
        onChange={(e) => setNewSql(e.target.value)}
        rows={4}
        className="min-h-52 font-mono text-sm p-2 bg-gray-50 border border-gray-300"
      />
    </Modal>
  );
};

export default AddQueryModal;
