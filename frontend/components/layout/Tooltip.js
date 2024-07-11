import React from "react";
import { Tooltip } from "antd/lib";

const CustomTooltip = ({ tooltipText, mainText }) => {
  return (
    <Tooltip title={tooltipText}>
      <span>{mainText}</span>
    </Tooltip>
  );
};

export default CustomTooltip;
