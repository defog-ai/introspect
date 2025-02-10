import { useEffect, useState } from "react";
import { CircleCheck, CircleX } from "lucide-react";

function ReportStatus({ status }) {
  const [displayStatus, setDisplayStatus] = useState("");

  // Convert status to sentence case (first letter capital, rest lowercase)
  const toSentenceCase = (status) => {
    if (!status) return "";
    return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
  };

  useEffect(() => {
    if (!status) return;
    const sentenceCased = toSentenceCase(status);
    setDisplayStatus(sentenceCased);
  }, [status]);

  const statusIcon =
    displayStatus === "Done" ? (
      <CircleCheck className="w-3 text-emerald-500" />
    ) : displayStatus === "Error" ? (
      <CircleX className="w-3 text-red-500" />
    ) : null;

  return (
    <div className="flex items-center space-x-2">
      {statusIcon}
      <span
        className={`text-lg font-semibold ${
          displayStatus === "Done"
            ? "text-green-500"
            : displayStatus === "Error"
            ? "text-red-500"
            : "text-purple-500 animate-pulse-text"
        }`}
      >
        {displayStatus || "Processing"}
      </span>
      <style jsx global>{`
        @keyframes pulseText {
          0%,
          100% {
            opacity: 0.5;
          }
          50% {
            opacity: 1;
          }
        }
        .animate-pulse-text {
          animation: pulseText 1.5s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

export default ReportStatus;
