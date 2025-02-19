import React from "react";
import { Popover } from "@defogdotai/agents-ui-components/core-ui";

const CustomTooltip = ({ tooltipText, mainText }) => {
  return (
    <Popover
      content={tooltipText}
      placement="top"
      trigger="hover"
      className="inline-block"
    >
      <span className="cursor-help">{mainText}</span>
    </Popover>
  );
};

export default CustomTooltip;
