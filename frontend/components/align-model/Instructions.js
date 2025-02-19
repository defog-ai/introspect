import { SpinningLoader, Button } from "@defogdotai/agents-ui-components/core-ui";

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
    <div className="relative">
      {(isLoading || isUpdatingInstructions) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-white bg-opacity-70 z-10">
          <SpinningLoader className="text-blue-500" />
          <span className="mt-2 text-gray-600">
            {isUpdatingInstructions ? "Updating Instructions..." : "Loading Instructions"}
          </span>
        </div>
      )}
      <div className={isLoading || isUpdatingInstructions ? "pointer-events-none" : ""}>
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
      </div>
    </div>
    <Button
      variant="primary"
      className="mt-4 px-4 py-2 min-w-[200px] flex items-center justify-center"
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
