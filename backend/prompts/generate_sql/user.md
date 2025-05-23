**Database Schema**
```
{table_metadata_ddl}
```

**Output format**
Return only a markdown code block that contains the SQL—no commentary, explanations, or additional text.

**Guidelines**
1. *Case insensitive string search*: Unless a reference query explicitly shows otherwise —or the column represents a categorical value— perform case-insensitive fuzzy matching
2. All ratios must be floats. eg: `CAST(numerator AS FLOAT) / denominator`
3. "By month" means "by month and year"
4. Try to order the results meaningfully. Handle NULL values in ORDER BY statements by using the NULLS LAST modifiers (or your SQL dialect’s equivalent).
5. Remember that only floats can be rounded. INT values cannot be rounded.
6. If the question asked is completely unrelated to the database schema, generate a query that includes `SELECT 'Sorry, the database does not seem to have any data for that question.' AS answer;`. Only do this if the question is completely unrelated. If not, try your best to answer the question.

{instructions}
{golden_queries_prompt}

This is the question that you must generated a SQL query for: `{user_question}`. 