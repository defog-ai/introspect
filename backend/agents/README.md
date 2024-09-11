# Agents

## Adding a new tool

To add a new tool that the agent/oracle can use, you need to:

1. Define the function code for your tool in the appropriate category in `agents/planner_executor/toolboxes/<tool_category>/tools.py`
2. Add the metadata for your tool in the `tools` object in `agents/planner_executor/tool_helpers/all_tools.py`
