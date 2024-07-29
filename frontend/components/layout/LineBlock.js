import React, { useState } from "react";
import { Input } from "antd";
import { EditOutlined } from "@ant-design/icons";

const LineBlock = ({ helperText, mainText, onUpdate, isEditable }) => {
  const [editableText, setEditableText] = useState(mainText);
  const [editMode, setEditMode] = useState(false);

  const handleUpdate = () => {
    onUpdate(editableText); // Update the parent state with new text
    setEditMode(false); // Exit edit mode
  };

  const toggleEdit = () => setEditMode(!editMode);

  return (
    <div
      style={{
        backgroundColor: "#FFFAF0", // Light orange background
        borderLeft: "5px solid #FFA500", // Orange left border for emphasis
        padding: "10px",
        margin: "10px 0",
        fontFamily: "Monospace", // Font style similar to code
        color: "#333",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <span>{helperText}&nbsp;</span>
      {editMode ? (
        <Input
          value={editableText}
          onChange={(e) => setEditableText(e.target.value)}
          onPressEnter={handleUpdate}
          onBlur={handleUpdate}
          autoFocus
          style={{ flex: 1 }}
        />
      ) : (
        <span style={{ flex: 1 }}>{editableText}</span>
      )}
      {isEditable && (
        <EditOutlined
          onClick={toggleEdit}
          style={{ cursor: "pointer", color: "#FFA500", marginLeft: "10px" }}
        />
      )}
    </div>
  );
};

export default LineBlock;
