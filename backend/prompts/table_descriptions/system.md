# Task

Your task is to infer and generate informative table descriptions for a given
database's schema.

# Instructions

For each table:
    - Mention if the table is a dimension table or a fact table, and if it is a dimension table, what the main fact table is that references it.
    - Describe what the table contains in at most 1 sentence, and what the purpose of the table is.
    - Describe what each row in the table uniquely identifies in brackets.

Return the table descriptions as a TableDescriptions object which contains a list of TableDescription objects, where each object contains the table name and the table description in a single sentence.

# Example

Example Input 1:
```sql
CREATE TABLE table_1 (
    user_id INT,
    user_name VARCHAR(255),
    user_email VARCHAR(255),
    user_created_at TIMESTAMP
);
CREATE TABLE table_2 (
    login_id INT,
    user_id INT,
    login_time TIMESTAMP,
    login_ip VARCHAR(255),
    login_status VARCHAR(255)
);
CREATE TABLE table_3 (
    ip_address VARCHAR(255),
    ip_city VARCHAR(255),
    ip_region VARCHAR(255),
    ip_country VARCHAR(255)
);
```

Example Output 1:
```python
TableDescriptions(
    table_descriptions=[
        TableDescription(
            table_name="table_1",
            table_description="Dimension table containing user information (1 row per user id)"
        ),
        TableDescription(
            table_name="table_2",
            table_description="Fact table containing login information (1 row per login attempt)"
        ),
        TableDescription(
            table_name="table_3",
            table_description="Dimension table containing IP address information (1 row per IP address)"
        )
    ]
)
```
