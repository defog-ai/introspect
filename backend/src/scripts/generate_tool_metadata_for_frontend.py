# import inspect
# import json
# import os
# import sys

# # add to path
# module_path = os.path.abspath(os.path.join(".."))
# if module_path not in sys.path:
#     sys.path.append(module_path)

# from agents.planner_executor.execute_tool import parse_function_signature
# from agents.planner_executor.tool_helpers.all_tools import tools


# def generate_tool_json_for_frontend():
#     tool_json = {}
#     for key in tools:
#         tool = tools[key]
#         tool_name = tool["name"]
#         tool_fn = tool["fn"]
#         tool_function_signature = parse_function_signature(
#             inspect.signature(tool_fn).parameters, tool_name
#         )
#         tool_json[tool_name] = {
#             "function_name": tool_name,
#             "tool_name": tool["tool_name"],
#             "function_signature": tool_function_signature,
#             "toolbox": tool["toolbox"],
#         }
#     return tool_json


# j = generate_tool_json_for_frontend()
# j_str = json.dumps(j, indent=2)
# print(j_str)


# # j_str = json.dumps(j, indent=2)

# # j_str = "export const toolsMetadata = " + j_str

# # # prunt current di
# # print(os.getcwd())

# # f_path = "../../utils/tools_metadata.js"
# # f_path = os.path.join(os.getcwd(), f_path)

# # with open(f_path, "w") as f:
# #     f.write(j_str)
# #     f.close()

# # print("Wrote tools metadata to utils/tools_metadata.js")
