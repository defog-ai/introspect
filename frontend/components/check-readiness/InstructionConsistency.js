import React, { useState } from "react";
import { Button, Table, Tooltip } from "antd";
import { QuestionCircleOutlined } from "@ant-design/icons";

const InstructionConsistency = ({
  loadingInstructionConsistency,
  instructionConsistencyRating,
  inconsistentInstructions,
  inconsistentReason,
  checkInstructionConsistency,
}) => {
  const [isVisible, setIsVisible] = useState(false);

  const getColor = () => {
    return instructionConsistencyRating.indexOf("Excellent") === -1
      ? "red"
      : "green";
  };

  const getMessage = () => {
    if (!instructionConsistencyRating) return "";
    return instructionConsistencyRating.indexOf("Excellent") === -1
      ? "Your instructions have inconsistencies!"
      : "Excellent: Your instructions are consistent!";
  };

  const dataSource = inconsistentInstructions.map((instruction, index) => ({
    key: index,
    instruction,
    reason: inconsistentReason[index],
  }));

  const columns = [
    {
      title: "Inconsistent Instruction",
      dataIndex: "instruction",
      key: "instruction",
      width: "50%",
      align: "center",
    },
    {
      title: "Reason for Inconsistency",
      dataIndex: "reason",
      key: "reason",
      width: "50%",
      align: "center",
    },
  ];

  const handleClick = () => {
    if (!isVisible) checkInstructionConsistency();
    setIsVisible(!isVisible);
  };

  return (
    <div style={{ padding: "1.5em", paddingBottom: "0em" }}>
      <Button
        type="primary"
        onClick={handleClick}
        loading={loadingInstructionConsistency}
        ghost
        style={{ width: "100%" }}
      >
        {isVisible
          ? "Hide Instructions Consistency Check"
          : "2. Check Instructions Consistency"}
        <Tooltip title="Make sure you instructions are consistent and do not contradict each other">
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
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              marginTop: "2rem",
              marginBottom: "1.5rem",
            }}
          >
            <p
              style={{
                marginTop: "1.5em",
                color: getColor(),
                fontWeight: "bold",
                margin: "auto",
                fontSize: "1.5rem",
              }}
            >
              {getMessage()}
            </p>
          </div>
          {instructionConsistencyRating && (
            <>
              <div style={{ maxHeight: "300px", overflowY: "auto" }}>
                <Table
                  dataSource={dataSource}
                  columns={columns}
                  pagination={false}
                />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
};

export default InstructionConsistency;
