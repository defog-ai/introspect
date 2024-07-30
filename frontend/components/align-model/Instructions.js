import { Button, Spin } from "antd";

const Instructions = ({
  glossary,
  setGlossary,
  updateGlossary,
  isLoading,
  isUpdatingInstructions,
}) => (
  <div className="w-full p-4">
    <h2 className="text-2xl font-bold mb-3">Instructions</h2>
    <p className="mb-4 text-gray-700">
      These instructions are used by the model as a guide for the SQL queries
      that it generates. You can change them below.
    </p>
    <Spin
      spinning={isLoading || isUpdatingInstructions}
      tip={
        isUpdatingInstructions
          ? "Updating Instructions..."
          : "Loading Instructions"
      }
    >
      <textarea
        className="w-full min-h-28 p-2 border rounded border-gray-300 shadow-sm focus:border-gray-500 focus:ring focus:ring-gray-200 transition duration font-mono"
        value={glossary}
        onChange={(e) => setGlossary(e.target.value)}
        rows={8}
        disabled={isLoading}
      />
    </Spin>
    <Button
      type="primary"
      className="mt-4 h-auto p-2 min-w-56"
      onClick={updateGlossary}
      disabled={isLoading || isUpdatingInstructions}
    >
      Update Instructions
    </Button>
  </div>
);

export default Instructions;
