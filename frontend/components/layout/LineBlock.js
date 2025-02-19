import React, { useState } from "react";
import { Input } from "@defogdotai/agents-ui-components/core-ui";
import { EditOutlined } from "@ant-design/icons";

const LineBlock = ({ helperText, mainText, onUpdate, isEditable, inputModeOn = false }) => {
  const [editableText, setEditableText] = useState(mainText);
  const [editMode, setEditMode] = useState(inputModeOn);

  const handleUpdate = () => {
    onUpdate(editableText);
    setEditMode(false);
  };

  const toggleEdit = () => setEditMode(!editMode);

  return (
    <div className="bg-[#FFFAF0] border-l-4 border-[#FFA500] p-2.5 my-2.5 font-mono text-gray-700 flex justify-between items-center">
      <span className="shrink-0">{helperText}&nbsp;</span>
      <div className="flex-1 min-w-0">
        {editMode ? (
          <Input
            value={editableText}
            onChange={(e) => setEditableText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleUpdate()}
            onBlur={handleUpdate}
            autoFocus
            inputClassNames="w-full bg-white dark:bg-dark-bg-secondary border border-gray-300 dark:border-dark-border dark:text-dark-text-primary"
          />
        ) : (
          <span>{editableText}</span>
        )}
      </div>
      {isEditable && (
        <EditOutlined
          onClick={toggleEdit}
          className="cursor-pointer text-[#FFA500] ml-2.5 hover:opacity-80 shrink-0"
        />
      )}
    </div>
  );
};

export default LineBlock;
