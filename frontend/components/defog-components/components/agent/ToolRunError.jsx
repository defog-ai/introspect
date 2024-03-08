import { MdErrorOutline } from "react-icons/md";

export function ToolRunError({ error_message = null }) {
  return (
    <div className="tool-run-error">
      <div className="tool-run-error-icon">
        <MdErrorOutline /> An error occurred
      </div>
      <div className="tool-run-error-message">
        {error_message || "Something went wrong"}
      </div>
    </div>
  );
}
