You are given:

1. **Schema (DDL)**
{table_metadata_ddl}

2. **User context**
<context>
{instructions}
</context>

3. **User question**
`{question}`

---

### Your task  
Decide whether the user’s question can be answered unambiguously using only the schema and context above.

- **If it can:** output nothing (an empty string).  
- **If it cannot:** output **one** short, direct clarifying question that removes the ambiguity.

### When to ask a clarifying question  
Ask **only** when both of the following are true:

1. The user’s intent is unclear with respect to the schema or context, **and**  
2. The question cannot be answered as-is.

Your default should be to NOT ask a clarifying question, unless it is strongly needed.

*Do **not** ask about table or column names, or ask how a term maps to a table or column in the DDL.*

---

### Output format  
Return the clarifying question **alone**—no preamble, explanations, or extra text.
