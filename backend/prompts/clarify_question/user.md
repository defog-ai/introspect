A non-technical user asked me to get a SQL query for answering a question about a dataset.

These were the DDL statements for the dataset:
{table_metadata_ddl}

And this was the context that the user provided me:
<context>
{instructions}
</context>

Can the question be answered by the context provided, or does it require further clarification?

If it requires further clarification, can you please generate a specific clarification question that I can ask the user to make it unambigious?

Most of the time, a clarification will NOT be needed. ONLY ask a clarifying question if:
- the intent of the user's question is ambiguous wrt the DDL statements and/or the context
- the question cannot be answered by the instructions given, or by the DDL

If a clarifying question is needed, ensure that it is short, clear, and concise. Do not ask questions about what tables and/or columns the user might be referring to. ONLY ask questions if it seems like answering the question (given the DDL/instructions) would be ambiguous.

The user's question is: `{question}`.

Please generate a clarifying question (if needed) for it. Return just the clarifying question, without any preamble, justification, or any other text.