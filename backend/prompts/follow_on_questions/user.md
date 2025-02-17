Please suggest follow-on questions to ask on a database, given an initial question, instructions about how to answer that question, and a database schema.

This is the database schema:
```sql
{table_metadata_ddl}
```

These are some instructions about the database:
<instructions>
{instructions}
</instructions>

What 3 questions would be a good question to ask after this question? Here are some examples you can consider to decide which questions to ask:

Original Question: How many restaurants are there in the dataset?
Response: The following questions would be good to ask after this question:
1. Can you give a breakdown of the types of restaurants in the dataset?
2. What is the average rating of the restaurants in the dataset, by city?
3. What is the top restaurant in each city

Original Question: What are our total activations this year?
Response: The following questions would be good to ask after this question:
1. Can you compare this against the previous year?
2. Can you break this down by region?
3. What title is driving the most activations this year?

Only return the follow-on questions, without a preamble or any other text.

The question asked by the user was:
{question}