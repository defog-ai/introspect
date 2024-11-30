import { useEffect, useState } from "react";
import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";

function ReportStatus({ status }) {
  const [displayStatus, setDisplayStatus] = useState("");
  const [animate, setAnimate] = useState(false);

  // Capitalize the first letter of each word in the status
  const capitalizeStatus = (status) =>
    status
      .split(" ")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(" ");

  useEffect(() => {
    if (!status) return;

    // Trigger animation whenever status changes
    setAnimate(true);
    const capitalized = capitalizeStatus(status);
    setDisplayStatus(capitalized);

    const timeout = setTimeout(() => {
      setAnimate(false);
    }, 500); // Animation duration

    return () => clearTimeout(timeout);
  }, [status]);

  const statusIcon =
    displayStatus === "Done" ? (
      <CheckCircleOutlined className="text-emerald-500" />
    ) : displayStatus === "Error" ? (
      <CloseCircleOutlined className="text-red-500" />
    ) : null;

  return (
    <div className="flex items-center space-x-2">
      {statusIcon}
      <span
        className={`text-lg font-semibold relative overflow-hidden ${
          displayStatus === "Done"
            ? "text-green-500"
            : displayStatus === "Error"
            ? "text-red-500"
            : "text-gray-500"
        }`}
      >
        <span
          className={`inline-block ${
            animate ? "animate-blur" : ""
          }`}
        >
          {displayStatus || "Loading..."}
        </span>
      </span>
    </div>
  );
}

export default ReportStatus;
