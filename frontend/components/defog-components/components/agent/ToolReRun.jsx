import { Button } from "antd";

export function ToolReRun({
  onClick = () => {},
  text = "Re run",
  loading = false,
  className = "tool-re-run",
}) {
  return (
    <div
      className={
        "tool-action-button " +
        className +
        (loading ? " tool-action-button-loading" : "")
      }
      onClick={onClick}
    >
      <p>{text}</p>
    </div>
  );
}
