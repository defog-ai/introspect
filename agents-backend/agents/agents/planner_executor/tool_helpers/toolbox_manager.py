from agents.planner_executor.toolboxes.toolbox_prompts import toolbox_prompts

all_toolboxes = ["cancer-survival", "f1"]


def get_tool_library(toolboxes=[]):
    toolboxes += ["data-fetching", "stats", "plots", "cancer-survival"]
    toolboxes = list(set(toolboxes))
    prompt = ""
    # now get the prompt for each
    for toolbox in toolboxes:
        try:
            if (
                toolbox in toolbox_prompts
                and type(toolbox_prompts[toolbox]) == str
                and toolbox_prompts[toolbox].strip() != ""
            ):
                prompt += "\n\n" + toolbox_prompts[toolbox].strip()
            else:
                raise ValueError(f"Toolbox {toolbox} not found.")
        except Exception as e:
            print(
                f"Either toolbox: {toolbox} was not found or the prompt description is empty.\nAre you sure you have the right toolbox name and have added the descriptions to the toolbox_prompts.py file?\n"
            )
            continue

    return prompt
