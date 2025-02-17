Please generate a SQL query that answers this question :`{user_question}`. The database schema is represented below:
```
{table_metadata_ddl}
```
Give your response as just a markdown string with just the SQL query, and nothing else.

Always follow these instructions for generating the SQL query:
1. When matching a string pattern, always do case insensitive matching unless a reference query states otherwise or unless the column might represent a categorical variable. You can chain multiple patterns using the OR operator. (e.g. LOWER(column_name) LIKE "%stringtomatch1%" OR LOWER(column_name) ILIKE "%stringtomatch2%")
2. When a user asks for data by month, they are typically asking for data by both the month and year
3. Always remember to cast any ratios as floats.
4. To handle NULL values in ORDER BY statements, use the NULLS LAST modifiers or equivalent.
5. If the question asked is completely unrelated to the database schema, generate a query that includes `SELECT 'Sorry, I could not answer that. Could you please rephrase your question?' AS answer;`
{instructions}
{golden_queries_prompt}