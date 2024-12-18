export function ToolEditorInput({ name = null, description = null }) {
  return (
    <div className="w-40">
      <div className="text-sm rounded-t-md font-semibold text-gray-900 p-1 bg-gray-100 mb-1">
        {name}
      </div>
      <div className="p-1 overflow-scroll">
        <div>{description}</div>
      </div>
    </div>
  );
}
