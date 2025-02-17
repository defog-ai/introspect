import pytest

from typing import List
from utils_sql import add_hard_filters
from request_models import HardFilter

@pytest.mark.parametrize(
    "sql, hard_filters, expected",
    [
        (
            # Simple query, no WHERE
            "SELECT * FROM my_table",
            [HardFilter(table_name="my_table", column_name="foo", operator="=", value="bar")],
            "SELECT * FROM my_table WHERE my_table.foo = 'bar'"
        ),
        (
            # Simple query with existing WHERE
            "SELECT * FROM my_table WHERE my_table.id > 100",
            [HardFilter(table_name="my_table", column_name="status", operator="=", value="active")],
            # Expect the extra condition to be ANDed in
            "SELECT * FROM my_table WHERE my_table.id > 100 AND my_table.status = 'active'"
        ),
        (
            # Query with alias
            "SELECT t.col1, t.col2 FROM my_table t",
            [HardFilter(table_name="my_table", column_name="foo", operator="=", value="bar")],
            "SELECT t.col1, t.col2 FROM my_table AS t WHERE t.foo = 'bar'"
        ),
        (
            # Multiple filters, same table
            "SELECT t.col1 FROM my_table t",
            [
                HardFilter(table_name="my_table", column_name="foo", operator="=", value="bar"),
                HardFilter(table_name="my_table", column_name="baz", operator="=", value="qux"),
            ],
            # The order in which the conditions appear may differ depending on iteration order,
            # but both conditions should be added ANDed together.
            # One possible expected result:
            "SELECT t.col1 FROM my_table AS t WHERE t.foo = 'bar' AND t.baz = 'qux'"
        ),
        (
            # multiple filters with a pre-existing WHERE
            "SELECT t.col1 FROM my_table t WHERE t.id > 100",
            [
                HardFilter(table_name="my_table", column_name="foo", operator="=", value="bar"),
                HardFilter(table_name="my_table", column_name="baz", operator="=", value="qux"),
            ],
            # The order in which the conditions appear may differ depending on iteration order,
            # but both conditions should be added ANDed together.
            # One possible expected result:
            "SELECT t.col1 FROM my_table AS t WHERE t.id > 100 AND t.foo = 'bar' AND t.baz = 'qux'"
        ),
        (
            # filters on a table that does not appear in the query
            "SELECT t.col1 FROM my_table t",
            [HardFilter(table_name="other_table", column_name="foo", operator="=", value="bar")],
            # The order in which the conditions appear may differ depending on iteration order,
            # but both conditions should be added ANDed together.
            # One possible expected result:
            "SELECT t.col1 FROM my_table AS t"
        ),
        (
            # test out a GTE filter
            "SELECT COUNT(*) AS total_listings FROM listing",
            [HardFilter(table_name="listing", column_name="listtime", operator=">=", value="2024-01-01")],
            "SELECT COUNT(*) AS total_listings FROM listing WHERE listing.listtime >= '2024-01-01'"
        )
    ],
)
def test_add_sql_filters_basic(sql: str, hard_filters: List[HardFilter], expected: str):
    """
    Test basic scenarios including:
        - queries without WHERE
        - queries with existing WHERE
        - queries with alias
        - multiple filters on the same table
    """
    result = add_hard_filters(sql, hard_filters)
    # Depending on how the SQL is rendered, it might differ slightly (e.g. spacing),
    # so normalizing whitespace or comparing sorted tokens could be appropriate.
    # For simplicity, let's compare direct strings:
    assert result.strip().lower() == expected.strip().lower(), f"\nGot: {result}\nExpected: {expected}"


def test_add_sql_filters_cte():
    """
    Test a query with a CTE reference. The filter should only apply to the table
    referenced in the CTE or main query, not to other named tables.
    """
    sql = """
    WITH last_month AS (
        SELECT 
            1 AS join_key,
            COUNT(DISTINCT user_id) AS user_count
        FROM users
        WHERE created_at >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
        AND created_at < date_trunc('month', CURRENT_DATE)
    ),
    this_month AS (
        SELECT 
            1 AS join_key,
            COUNT(DISTINCT user_id) AS user_count
        FROM users
        WHERE created_at >= date_trunc('month', CURRENT_DATE)
        AND created_at < date_trunc('month', CURRENT_DATE + INTERVAL '1 month')
    )
    SELECT 
        tm.user_count AS this_month_count,
        lm.user_count AS last_month_count,
        (tm.user_count - lm.user_count) AS difference
    FROM last_month lm
    JOIN this_month tm USING (join_key);
    """
    hard_filters = [HardFilter(table_name="users", column_name="app_id", operator="=", value="foo")]
    
    expected_string = "WITH last_month AS (SELECT 1 AS join_key, COUNT(DISTINCT user_id) AS user_count FROM users WHERE created_at >= DATE_TRUNC('MONTH', CURRENT_DATE - INTERVAL '1 MONTH') AND created_at < DATE_TRUNC('MONTH', CURRENT_DATE) AND users.app_id = 'foo'), this_month AS (SELECT 1 AS join_key, COUNT(DISTINCT user_id) AS user_count FROM users WHERE created_at >= DATE_TRUNC('MONTH', CURRENT_DATE) AND created_at < DATE_TRUNC('MONTH', CURRENT_DATE + INTERVAL '1 MONTH') AND users.app_id = 'foo') SELECT tm.user_count AS this_month_count, lm.user_count AS last_month_count, (tm.user_count - lm.user_count) AS difference FROM last_month AS lm JOIN this_month AS tm USING (join_key)"
    # The main SELECT referencing cte should not get a filter
    # because it doesn't mention my_table, just the CTE name 'cte'.
    
    result = add_hard_filters(sql, hard_filters)
    
    # Verify that the CTE SELECT got the filter
    assert expected_string.lower() in result.lower()

def test_add_sql_filter_cte_complex():
    """
    Test a query with a CTE reference. The filter should only apply to the table
    referenced in the CTE or main query, not to other named tables.
    """
    sql = """
    WITH top_sources AS (
        SELECT source, SUM(users) AS total_users
        FROM gaoverall
        GROUP BY source
        ORDER BY total_users DESC NULLS LAST LIMIT 4
    ), total_users AS (
        SELECT SUM(users) AS total_users
        FROM gaoverall
    )
    SELECT
        source, (ts.total_users::float)/(tu.total_users) as percentage_of_total_users
    FROM top_sources ts, total_users tu
    """
    hard_filters = [
        HardFilter(table_name="gaoverall", column_name="user_id", operator="=", value="foo"),
        HardFilter(table_name="gapageviews", column_name="user_id", operator="=", value="foo")
    ]
    expected_string = "WITH top_sources AS (SELECT source, SUM(users) AS total_users FROM gaoverall WHERE gaoverall.user_id = 'foo' GROUP BY source ORDER BY total_users DESC NULLS LAST LIMIT 4), total_users AS (SELECT SUM(users) AS total_users FROM gaoverall WHERE gaoverall.user_id = 'foo') SELECT source, (CAST(ts.total_users AS DOUBLE PRECISION)) / (tu.total_users) AS percentage_of_total_users FROM top_sources AS ts, total_users AS tu"
    
    result = add_hard_filters(sql, hard_filters)
    assert expected_string.lower() in result.lower()


def test_add_sql_filters_subquery():
    """
    Test a query that has a subquery in the FROM clause. 
    We expect the subquery's SELECT to get the filter if it references my_table.
    """
    sql = """
    SELECT main.col1
    FROM (
        SELECT id AS col1 FROM my_table WHERE id < 100
    ) AS main
    """
    hard_filters = [HardFilter(table_name="my_table", column_name="foo", operator="=", value="bar")]
    
    expected_substring = "SELECT id AS col1 FROM my_table WHERE id < 100 AND my_table.foo = 'bar'"
    
    result = add_hard_filters(sql, hard_filters)
    assert expected_substring.lower() in result.lower()


def test_add_sql_filters_no_match():
    """
    Test that no changes are made if the table in the query does not match
    any of the HardFilter table_names.
    """
    sql = "SELECT * FROM some_other_table"
    hard_filters = [HardFilter(table_name="my_table", column_name="foo", operator="=", value="bar")]
    
    # We expect the result to be the same as the original
    result = add_hard_filters(sql, hard_filters)
    assert result.strip().lower() == sql.strip().lower()
