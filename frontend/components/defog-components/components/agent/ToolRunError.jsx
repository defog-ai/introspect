import { ExclamationCircleIcon } from "@heroicons/react/20/solid";

export function ToolRunError({ error_message = null }) {
  return (
    <div className="tool-run-error">
      <div className="tool-run-error-icon flex flex-row items-start">
        <ExclamationCircleIcon className="h-5 w-5 stroke-rose-400 text-transparent mr-1" />{" "}
        An error occurred
      </div>
      <div className="tool-run-error-message">
        {error_message || "Something went wrong"}
      </div>
    </div>
  );
}
