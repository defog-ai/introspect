from db_utils import get_all_tools
from utils import create_simple_tool_types, embed_string
import yaml


async def get_tool_library_prompt(toolboxes=[], user_question=None):
    toolboxes += ["data_fetching", "stats", "plots"]
    toolboxes = list(set(toolboxes))
    prompt = []

    user_question_embedding = await embed_string(user_question)

    # get pruned tools based on user question
    err, tools = get_all_tools(
        user_question_embedding,
        mandatory_tools=[
            "data_fetcher_and_aggregator",
            "global_dict_data_fetcher_and_aggregator",
        ],
    )

    if err:
        return ""

    print("Pruned tools:", [x["function_name"] for x in tools.values()])

    # now get the prompt for each
    for _, tool in tools.items():
        # if it's disabled, skip
        if tool["disabled"]:
            continue

        # if it's in toolboxes
        toolbox = tool["toolbox"]
        if toolbox in toolboxes:
            tool_inputs_prompt = {}
            for input in tool["input_metadata"]:
                tool_inputs_prompt[input["name"]] = (
                    f"{create_simple_tool_types(input['type'])} - {input['description']}"
                )

            tool_outputs_prompt = {}
            for output in tool["output_metadata"]:
                tool_outputs_prompt[output["name"]] = (
                    f"{create_simple_tool_types(output.get('type', 'pandas.core.frame.DataFrame'))}, {output['description']}"
                )

            prompt.append(
                {
                    "tool_name": tool["function_name"],
                    "description": tool["description"],
                    "inputs": tool_inputs_prompt,
                    "outputs": tool_outputs_prompt,
                }
            )

    prompt = yaml.dump(prompt, sort_keys=False)

    return prompt


# print(get_tool_library_prompt())
