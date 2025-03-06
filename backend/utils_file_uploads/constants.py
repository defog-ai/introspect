"""
Constants used throughout the utils package.
"""

# PostgreSQL reserved words for column name sanitization
POSTGRES_RESERVED_WORDS = {
    "select", "from", "where", "join", "table", "order", "group", "by", 
    "create", "drop", "insert", "update", "delete", "alter", "column", "user", 
    "and", "or", "not", "null", "true", "false", "primary", "key", "foreign", 
    "unique", "check", "default", "index", "on", "as", "asc", "desc", "varchar", 
    "int", "bigint", "float", "decimal", "text", "boolean", "date", "timestamp",
}