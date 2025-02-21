from utils_join_hints import validate_join_keys

def test_validate_join_keys_valid_input():
    # Test with valid metadata and join keys
    metadata = [
        {"table_name": "users", "column_name": "id"},
        {"table_name": "orders", "column_name": "user_id"},
        {"table_name": "products", "column_name": "id"},
        {"table_name": "orders", "column_name": "product_id"}
    ]
    
    join_keys_list = [
        ["users.id", "orders.user_id"],
        ["products.id", "orders.product_id"]
    ]
    
    result = validate_join_keys(join_keys_list, metadata)
    assert result == join_keys_list

def test_validate_join_keys_invalid_keys():
    # Test with invalid join keys
    metadata = [
        {"table_name": "users", "column_name": "id"},
        {"table_name": "orders", "column_name": "user_id"}
    ]
    
    join_keys_list = [
        ["users.id", "orders.user_id"],
        ["products.id", "orders.product_id"],  # Invalid - products table doesn't exist
        ["users.nonexistent", "orders.user_id"]  # Invalid - column doesn't exist
    ]
    
    result = validate_join_keys(join_keys_list, metadata)
    assert result == [["users.id", "orders.user_id"]]

def test_validate_join_keys_invalid_format():
    # Test with incorrectly formatted join keys
    metadata = [
        {"table_name": "users", "column_name": "id"},
        {"table_name": "orders", "column_name": "user_id"}
    ]
    
    join_keys_list = [
        ["users.id", "invalid_format"],  # Missing table name
        ["users_id", "orders.user_id"],  # Missing dot separator
    ]
    
    result = validate_join_keys(join_keys_list, metadata)
    assert result == []

def test_validate_join_keys_empty_input():
    # Test with empty inputs
    metadata = [
        {"table_name": "users", "column_name": "id"},
        {"table_name": "orders", "column_name": "user_id"}
    ]
    
    assert validate_join_keys([], metadata) == []
    assert validate_join_keys([["users.id", "orders.user_id"]], []) == []

def test_validate_join_keys_invalid_metadata():
    # Test with invalid metadata entries
    metadata = [
        {"table_name": "users", "column_name": "id"},
        {"invalid_key": "value"},  # Missing required keys
        {"table_name": "orders"}  # Missing column_name
    ]
    
    join_keys_list = [
        ["users.id", "orders.user_id"]
    ]
    
    result = validate_join_keys(join_keys_list, metadata)
    assert result == []  # No valid join keys since metadata is invalid

def test_validate_join_keys_partial_valid():
    # Test with partially valid join keys in a group
    metadata = [
        {"table_name": "users", "column_name": "id"},
        {"table_name": "orders", "column_name": "user_id"}
    ]
    
    join_keys_list = [
        ["users.id", "orders.user_id", "invalid.column"],  # One invalid key in group
    ]
    
    result = validate_join_keys(join_keys_list, metadata)
    assert result == [["users.id", "orders.user_id"]] 