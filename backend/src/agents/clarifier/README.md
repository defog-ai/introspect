This agent starts whenever a new analysis is started.

The clarifier looks at the question, looks at the schema + glossary, and then checks if there are any clarifying questions it needs to ask the user.

If yes, it asks these questions, the user answers them, and the final responses are then sent over to a planner_executor.
