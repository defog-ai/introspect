import { Button, Spin } from "antd";

const Instructions = ({
  title,
  description,
  compulsoryGlossary,
  setCompulsoryGlossary,
  prunableGlossary,
  setPrunableGlossary,
  updateGlossary,
  updateGlossaryLoadingFunction,
  isLoading,
  isUpdatingInstructions,
}) => (
  <div className="w-full p-4 bg-gray-50 mb-5">
    <h2 className="text-xl mb-3 font-semibold">{title}</h2>
    <p className="mb-4 text-gray-700">{description}</p>
    <Spin
      spinning={isLoading || isUpdatingInstructions}
      tip={
        isUpdatingInstructions
          ? "Updating Instructions..."
          : "Loading Instructions"
      }
    >
      <h3 className="text-lg font-semibold">Compulsory Instructions</h3>
      <p className="text-sm text-gray-700 mb-2">
        These are the instructions that the model is given for every single SQL
        query that it generates.
      </p>
      <textarea
        className="w-full min-h-40 p-2 border rounded border-gray-300 shadow-sm focus:border-gray-500 focus:ring focus:ring-gray-200 transition duration resize-y text-sm text-gray-900 leading-normal"
        value={compulsoryGlossary}
        onChange={(e) => setCompulsoryGlossary(e.target.value)}
        rows={8}
        disabled={isLoading}
      />

      <h3 className="text-lg font-semibold mt-4">Supplementary Instructions</h3>
      <p className="text-sm text-gray-700 mb-2">
        These are the instructions that are specific to only specific kinds of
        questions.
      </p>

      <textarea
        className="w-full min-h-40 p-2 border rounded border-gray-300 shadow-sm focus:border-gray-500 focus:ring focus:ring-gray-200 transition duration resize-y text-sm text-gray-900 leading-normal"
        value={prunableGlossary}
        onChange={(e) => setPrunableGlossary(e.target.value)}
        rows={8}
        disabled={isLoading}
      />
    </Spin>
    <Button
      type="primary"
      className="mt-4 p-2 min-w-56"
      onClick={() =>
        updateGlossary(
          compulsoryGlossary,
          prunableGlossary,
          updateGlossaryLoadingFunction
        )
      }
      disabled={isLoading || isUpdatingInstructions}
    >
      Update Glossary
    </Button>
  </div>
);

export default Instructions;
