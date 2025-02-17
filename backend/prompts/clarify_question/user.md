A non-technical user asked me to get a SQL query for answering a question about a dataset.

These were the DDL statements for the dataset:
{table_metadata_ddl}

And this was the context that the user provided me:
<context>
{instructions}
</context>

Is this unambigious? And if not, can you please generate a clarification that I can ask the user to make it unambigious?

Most of the time, a clarification will NOT be needed. Your default answer should be "Not ambiguous. No clarifying question is needed." ONLY ask a clarifying question if:
- the intent of the user's question is highly ambiguous
- the question cannot be answered by the instructions given, or by the DDL

If a clarifying question is indeed needed, ensure that it is clear and concise, and is less than 20 words. Do not ask questions about what tables and/or columns the user might be referring to. ONLY ask questions if the intent of their question is ambiguous.
