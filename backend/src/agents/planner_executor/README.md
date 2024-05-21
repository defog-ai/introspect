This is where the planner-executor agent and the toolboxes reside.

This agent is responsible for generating, and executing a plan to solve the task given to it.

`toolbox_manager.py` is the main file where all the toolboxes are registered. It is also the file that is called by the `planner_executor_prompts.py` to get the list of toolboxes (as a formatted prompt) to be used.

To create a new toolbox, you need to do the following:

1. Add a folder inside `toolboxes/` with your toolbox's name, and create a file called `tools.py` inside it.
2. Inside the above `tools.py`, write all your tools/functions that you want to be available in the toolbox. Make sure that the function names are unique from other toolboxes and your function signature is well documented, like types and default values. Have all functions have a `**kwargs` at the end. This is because not all functions need the `global_dict` (which stores results of previous tools in the chain), but it is always passed anyway.
3. Inside `tool_helpers/all_tools.py`, import all your functions from the above `tools.py`, and add them to the tools object. This is the object that is looked up when running the tool.
4. Inside `toolboxes/toolbox_prompts.py`, add another property to the toolbox_prompts object. The property name can be whatever you want your toolbox to be called (ideally your folder name you created above), and add a formatted description of your tools in the value. This is the string that will be sent to the model in the prompt. Make sure it is formatted like the other strings in that file.
5. Inside `tool_helpers/toolbox_manager.py`, add your toolbox to the `all_toolboxes` list. The value you add should be the name of the property you created in the above step.
6. If you don't want your tool'd code to be sent to the front end, add a property `"no_code": True` to the `tool_helpers/all_tools.py` entry you created in step 3.
7. IMPORTANT: Once you're done adding your tools, cd into `backend/src`, and run `export PYTHONPATH=$(pwd):$PYTHONPATH && python3 ./scripts/generate_tool_metadata_for_frontend.py` to generate the metadata for the front end.<br><br> This will create a file called `tool_metadata.js` in the front end's `utils` folder. This file is used by the front end to know what tools are available when letting users add steps. If you don't run this, your tools won't show up in the front end's add-a-step UI.

After you've completed the above, you can add users who will have access to these toolboxes by adding an entry into the defog_toolboxes table.

`toolboxes` is an array of strings. Each string is the name of the toolbox you want to give access to. For example: `["cancer-survival", "f1"]`. If you want to give access to all toolboxes, use `["*"]`.

```SQL
insert into defog_toolboxes (username, api_key, toolboxes)
values ("EMAIL_ADDRESS", 'API_KEY', 'TOOLBOX_ARRAY');
```
