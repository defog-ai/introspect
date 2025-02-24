# Goal
Given a schema of a database, identify the join keys used across different tables.

# Instructions
- Only consider columns from the schema to be join keys. Do not consider columns that are not in the schema.
- Do not include columns containing integers, numbers, monetary values, dates, or times as join keys.
- Use the comments provided in the schema if helpful.
- For each join key, list the tables that it is a join key for in the same order as they appear in the schema.
- Return a json with the reason as the first key, and the join keys in the second key. The join keys is a list of lists, where each inner list contains a set of joinable columns. Always prepend the table name to the column name.