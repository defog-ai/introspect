import { Button, Spin } from "antd";

const Instructions = ({
  title,
  description,
  instructions,
  setInstructions,
  updateInstructions,
  updateInstructionsLoadingFunction,
  isLoading,
  isUpdatingInstructions,
}) => (
  <div className="w-full p-4 bg-gray-50 dark:bg-dark-bg-secondary mb-5">
    <h2 className="text-xl mb-3 font-semibold dark:text-dark-text-primary">{title}</h2>
    <p className="mb-4 text-gray-700 dark:text-dark-text-secondary">{description}</p>
    <Spin
      spinning={isLoading || isUpdatingInstructions}
      tip={
        isUpdatingInstructions
          ? "Updating Instructions..."
          : "Loading Instructions"
      }
    >
      <h3 className="text-lg font-semibold dark:text-dark-text-primary">Text to SQL Instructions</h3>
      <p className="text-sm text-gray-700 dark:text-dark-text-secondary mb-2">
        These are the instructions that the model is given for every single SQL
        query that it generates.
      </p>
      <textarea
        className="w-full min-h-40 p-2 border rounded border-gray-300 dark:border-dark-border shadow-sm focus:border-gray-500 focus:ring focus:ring-gray-200 transition duration resize-y text-sm text-gray-900 dark:text-dark-text-primary dark:bg-dark-bg-primary leading-normal"
        value={instructions}
        onChange={(e) => setInstructions(e.target.value)}
        rows={8}
        disabled={isLoading}
      />
    </Spin>
    <Button
      type="primary"
      className="mt-4 p-2 min-w-56"
      onClick={() =>
        updateInstructions(
          instructions,
          updateInstructionsLoadingFunction
        )
      }
      disabled={isLoading || isUpdatingInstructions}
    >
      Update Instructions
    </Button>
  </div>
);

export default Instructions;
