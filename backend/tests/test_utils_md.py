from utils_md import mk_create_table_ddl, mk_create_ddl
from request_models import TableDescription

def test_mk_create_table_ddl_basic():
    columns = [
        {"column_name": "id", "data_type": "int"},
        {"column_name": "name", "data_type": "text"}
    ]
    expected = """CREATE TABLE IF NOT EXISTS test_table (
  id int,
  name text
);
"""
    result = mk_create_table_ddl("test_table", columns)
    assert result == expected

def test_mk_create_table_ddl_with_description():
    columns = [
        {"column_name": "id", "data_type": "int"},
        {"column_name": "name", "data_type": "text"}
    ]
    table_description = "This is a test table"
    expected = """COMMENT ON TABLE test_table IS 'This is a test table';
CREATE TABLE IF NOT EXISTS test_table (
  id int,
  name text
);
"""
    result = mk_create_table_ddl("test_table", columns, table_description)
    assert result == expected

def test_mk_create_table_ddl_with_spaces():
    columns = [
        {"column_name": "user id", "data_type": "int"},
        {"column_name": "full name", "data_type": "text"}
    ]
    expected = """CREATE TABLE IF NOT EXISTS users (
  "user id" int,
  "full name" text
);
"""
    result = mk_create_table_ddl("users", columns)
    assert result == expected

def test_mk_create_ddl_single_table():
    metadata = [
        {"table_name": "users", "column_name": "id", "data_type": "int"},
        {"table_name": "users", "column_name": "name", "data_type": "text"}
    ]
    expected = """CREATE TABLE IF NOT EXISTS users (
  id int,
  name text
);
"""
    result = mk_create_ddl(metadata)
    assert result == expected

def test_mk_create_ddl_multiple_tables():
    metadata = [
        {"table_name": "users", "column_name": "id", "data_type": "int"},
        {"table_name": "users", "column_name": "name", "data_type": "text"},
        {"table_name": "orders", "column_name": "order_id", "data_type": "int"},
        {"table_name": "orders", "column_name": "user_id", "data_type": "int"}
    ]
    expected = """CREATE TABLE IF NOT EXISTS users (
  id int,
  name text
);
CREATE TABLE IF NOT EXISTS orders (
  order_id int,
  user_id int
);
"""
    result = mk_create_ddl(metadata)
    assert result == expected

def test_mk_create_ddl_with_schema():
    metadata = [
        {"table_name": "public.users", "column_name": "id", "data_type": "int"},
        {"table_name": "public.users", "column_name": "name", "data_type": "text"}
    ]
    expected = """CREATE SCHEMA IF NOT EXISTS public;
CREATE TABLE IF NOT EXISTS users (
  id int,
  name text
);
"""
    result = mk_create_ddl(metadata)
    assert result == expected

def test_mk_create_ddl_with_table_descriptions():
    metadata = [
        {"table_name": "users", "column_name": "id", "data_type": "int"},
        {"table_name": "users", "column_name": "name", "data_type": "text"}
    ]
    table_descriptions = [
        TableDescription(table_name="users", table_description="User information table")
    ]
    expected = """COMMENT ON TABLE users IS 'User information table';
CREATE TABLE IF NOT EXISTS users (
  id int,
  name text
);
"""
    result = mk_create_ddl(metadata, table_descriptions)
    assert result == expected

def test_mk_create_ddl_multiple_schemas():
    metadata = [
        {"table_name": "public.users", "column_name": "id", "data_type": "int"},
        {"table_name": "public.users", "column_name": "name", "data_type": "text"},
        {"table_name": "analytics.events", "column_name": "event_id", "data_type": "int"},
        {"table_name": "analytics.events", "column_name": "event_type", "data_type": "text"}
    ]
    expected = """CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS users (
  id int,
  name text
);
CREATE TABLE IF NOT EXISTS events (
  event_id int,
  event_type text
);
"""
    result = mk_create_ddl(metadata)
    assert result == expected 

def test_mk_create_ddl_multiple_schemas_with_table_descriptions():
    metadata = [
        {"table_name": "public.users", "column_name": "id", "data_type": "int"},
        {"table_name": "public.users", "column_name": "name", "data_type": "text"},
    ]
    table_descriptions = [
        TableDescription(table_name="users", table_description="User information table")
    ]
    expected = """CREATE SCHEMA IF NOT EXISTS public;
COMMENT ON TABLE users IS 'User information table';
CREATE TABLE IF NOT EXISTS users (
  id int,
  name text
);
"""
    result = mk_create_ddl(metadata, table_descriptions)
    assert result == expected