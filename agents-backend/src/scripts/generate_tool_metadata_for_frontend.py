import inspect
import json
import os
from agents.planner_executor.execute_tool import parse_function_signature
from agents.planner_executor.tool_helpers.all_tools import tools


def generate_tool_json_for_frontend():
    tool_json = {}
    for tool in tools:
        tool_name = tool["name"]
        tool_fn = tool["fn"]
        tool_function_signature = parse_function_signature(
            inspect.signature(tool_fn).parameters, tool_name
        )
        tool_json[tool_name] = {
            "name": tool_name,
            "display_name": tool["display_name"],
            "function_signature": tool_function_signature,
        }
    return tool_json


j = generate_tool_json_for_frontend()
j_str = json.dumps(j, indent=2)
print(j_str)


# j_str = json.dumps(j, indent=2)

# j_str = "export const toolsMetadata = " + j_str

# # prunt current di
# print(os.getcwd())

# f_path = "../../utils/tools_metadata.js"
# f_path = os.path.join(os.getcwd(), f_path)

# with open(f_path, "w") as f:
#     f.write(j_str)
#     f.close()

# print("Wrote tools metadata to utils/tools_metadata.js")
