# Task

Given a schema of a database, identify the join keys used across different tables.

# Instructions

- Only consider columns from the schema to be join keys. Do not consider columns that are not in the schema.
- Do not include date/time columns as join keys.
- Use the comments provided in the schema if helpful.
- For each join key, list the tables that it is a join key for in the same order as they appear in the schema.
- Return a json with the reason as the first key, and the join keys in the second key. The join keys is a list of lists, where each inner list contains a set of joinable columns. Always prepend the table name to the column name.

# Examples

## Example Input 1

```sql
COMMENT ON TABLE users IS 'Dimension table for users (1 row per user)';
CREATE TABLE users (
    id BIGINT,
    name VARCHAR(255),
    email VARCHAR(255)
);
CREATE TABLE orders (
    id BIGINT,
    uid BIGINT,
    pid BIGINT,
    amount DECIMAL(10, 2)
);
CREATE TABLE products (
    id BIGINT,
    name VARCHAR(255),
    price DECIMAL(10, 2)
);
```

## Example Output 1

```json
{
    "reason": "We have id's representing the user in the users table and the orders table. We also have id's representing the product in the orders and products tables. These are not date/time columns, so they are valid join keys.",
    "join_keys": [
        ["users.id", "orders.uid"],
        ["orders.pid", "products.id"]
    ]
}
```
