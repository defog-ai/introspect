import collections
import re
from typing import Dict, Optional, Tuple
import time
from datetime import datetime

import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
from sqlglot import exp, parse_one
from utils_df import mk_df
from generic_utils import is_sorry
from defog.query import async_execute_query_once
from request_models import ColumnMetadata, HardFilter, QuestionAnswer
from llm_api import O3_MINI, GPT_4O
from utils_md import get_metadata, mk_create_ddl
from utils_instructions import get_instructions
from utils_embedding import get_embedding
from utils_golden_queries import get_closest_golden_queries
from defog.llm.utils import chat_async
import sqlparse
from utils_logging import LOGGER, log_timings, save_timing
from db_utils import get_db_type_creds
import re

with open("./prompts/generate_sql/system.md", "r") as f:
    GENERATE_SQL_SYSTEM_PROMPT = f.read()

with open("./prompts/generate_sql/user.md", "r") as f:
    GENERATE_SQL_USER_PROMPT = f.read()

with open("./prompts/fix_sql/system.md", "r") as f:
    FIX_SQL_SYSTEM_PROMPT = f.read()

with open("./prompts/fix_sql/user.md", "r") as f:
    FIX_SQL_USER_PROMPT = f.read()


UNSAFE_KEYWORDS = ['CREATE', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'INSERT']
# Combine keywords into one regex pattern for efficiency
UNSAFE_REGEX = re.compile(r'\b(?:' + '|'.join(UNSAFE_KEYWORDS) + r')\b', re.IGNORECASE)


# make sure the query does not contain any malicious commands like drop, delete, etc.
def safe_sql(query: str):
    if query is None:
        query = ""
    return not UNSAFE_REGEX.search(query)


async def execute_sql(
    db_type: str,
    db_creds: Dict,
    sql: str,
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Asynchronously run the SQL query on the user's database using SQLAlchemy and return the results as a dataframe.
    Returns the error message if any to let upstream caller decide how they want to handle it.
    This is sometimes logged and ignored, or used for iterative generation.
    """
    err_msg = None
    if not sql:
        err_msg = "No SQL generated to execute"
        return None, err_msg

    if is_sorry(sql):
        err_msg = "Obtained Sorry SQL query"
        return None, err_msg
    
    if not safe_sql(sql):
        err_msg = "Unsafe SQL query"
        return None, err_msg

    try:

        colnames, rows = await async_execute_query_once(db_type, db_creds, sql)
        data = [list(row) for row in rows]
        df = mk_df(data, colnames)
    except Exception as e:
        err_msg = f"Error occurred in running SQL: {e}\nSQL: {sql}"
        df = None

    return df, err_msg


def deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = df.columns.tolist()
    if len(cols) != len(set(cols)):
        duplicates = [
            item for item, count in collections.Counter(cols).items() if count > 1
        ]
        for dup in duplicates:
            indices = [i for i, x in enumerate(cols) if x == dup]
            for i in indices:
                cols[i] = f"{dup}_{i}"
        df.columns = cols
    return df


def normalize_table(df: pd.DataFrame, question: str, sql: str = None) -> pd.DataFrame:
    """
    Normalizes a dataframe by:
    1. removing all duplicate rows
    2. sorting columns in alphabetical order
    3. sorting rows using values from first column to last (if question does not ask for ordering)
    4. resetting index
    """
    # remove duplicate rows, if any
    df = df.drop_duplicates()

    # sort columns in alphabetical order of column names
    sorted_df = df.reindex(sorted(df.columns), axis=1)

    # check if query_category is 'order_by' and if question asks for ordering
    has_order_by = False
    pattern = re.compile(r"\b(order|sort|arrange)\b", re.IGNORECASE)
    in_question = re.search(pattern, question.lower())  # true if contains
    if in_question:
        has_order_by = True

        if sql:
            # determine which columns are in the ORDER BY clause of the sql generated, using regex
            pattern = re.compile(r"ORDER BY[\s\S]*", re.IGNORECASE)
            order_by_clause = re.search(pattern, sql)
            if order_by_clause:
                order_by_clause = order_by_clause.group(0)
                # get all columns in the ORDER BY clause, by looking at the text between ORDER BY and the next semicolon, comma, or parantheses
                pattern = re.compile(r"(?<=ORDER BY)(.*?)(?=;|,|\)|$)", re.IGNORECASE)
                order_by_columns = re.findall(pattern, order_by_clause)
                order_by_columns = (
                    order_by_columns[0].split() if order_by_columns else []
                )
                order_by_columns = [
                    col.strip().rsplit(".", 1)[-1] for col in order_by_columns
                ]

                ascending = False
                # if there is a DESC or ASC in the ORDER BY clause, set the ascending to that
                if "DESC" in [i.upper() for i in order_by_columns]:
                    ascending = False
                elif "ASC" in [i.upper() for i in order_by_columns]:
                    ascending = True

                # remove whitespace, commas, and parantheses
                order_by_columns = [col.strip() for col in order_by_columns]
                order_by_columns = [
                    col.replace(",", "").replace("(", "") for col in order_by_columns
                ]
                order_by_columns = [
                    i
                    for i in order_by_columns
                    if i.lower()
                    not in ["desc", "asc", "nulls", "last", "first", "limit"]
                ]

                # get all columns in sorted_df that are not in order_by_columns
                other_columns = [
                    i for i in sorted_df.columns.tolist() if i not in order_by_columns
                ]

                # only choose order_by_columns that are in sorted_df
                order_by_columns = [
                    i for i in order_by_columns if i in sorted_df.columns.tolist()
                ]
                sorted_df = sorted_df.sort_values(
                    by=order_by_columns + other_columns, ascending=ascending
                )

                sorted_df = sorted_df[other_columns + order_by_columns]

    if not has_order_by:
        # sort rows using values from first column to last
        sorted_df = sorted_df.sort_values(by=list(sorted_df.columns))

    # reset index
    sorted_df = deduplicate_columns(sorted_df)
    sorted_df = sorted_df.reset_index(drop=True)
    return sorted_df


def compare_df(
    df_gold: pd.DataFrame,
    df_gen: pd.DataFrame,
    question: str,
    query_gold: str = None,
    query_gen: str = None,
) -> bool:
    """
    Compares two dataframes and returns True if they are the same, else False.
    query_gold and query_gen are the original queries that generated the respective dataframes.
    """
    # drop duplicates to ensure equivalence
    try:
        is_equal = df_gold.values == df_gen.values
        if is_equal.all():
            return True
    except:
        try:
            is_equal = df_gold.values == df_gen.values
            if is_equal:
                return True
        except:
            pass

    df_gold = normalize_table(df_gold, question, query_gold)
    df_gen = normalize_table(df_gen, question, query_gen)

    # perform same checks again for normalized tables
    if df_gold.shape != df_gen.shape:
        return False
    # fill NaNs with -99999 to handle NaNs in the dataframes for comparison
    df_gen.fillna(-99999, inplace=True)
    df_gold.fillna(-99999, inplace=True)
    is_equal = df_gold.values == df_gen.values
    try:
        return is_equal.all()
    except:
        return is_equal


def subset_df(
    df_sub: pd.DataFrame,
    df_super: pd.DataFrame,
    question: str,
    query_super: str = None,
    query_sub: str = None,
    verbose: bool = False,
) -> bool:
    """
    Checks if df_sub is a subset of df_super.
    """
    if df_sub.empty:
        return False  # handle cases for empty dataframes

    # make a copy of df_super so we don't modify the original while keeping track of matches
    df_super_temp = df_super.copy(deep=True)
    matched_columns = []
    df_sub = deduplicate_columns(df_sub)
    df_super_temp = deduplicate_columns(df_super_temp)
    for col_sub_name in df_sub.columns:
        col_match = False
        for col_super_name in df_super_temp.columns:
            col_sub = df_sub[col_sub_name].sort_values().reset_index(drop=True)
            col_super = (
                df_super_temp[col_super_name].sort_values().reset_index(drop=True)
            )

            try:
                assert_series_equal(
                    col_sub, col_super, check_dtype=False, check_names=False
                )
                col_match = True
                matched_columns.append(col_super_name)
                # remove col_super_name to prevent us from matching it again
                df_super_temp = df_super_temp.drop(columns=[col_super_name])
                break
            except AssertionError:
                continue

        if not col_match:
            if verbose:
                print(f"no match for {col_sub_name}")
            return False

    df_sub_normalized = normalize_table(df_sub, question, query_sub)

    # get matched columns from df_super, and rename them with columns from df_sub, then normalize
    df_super_matched = df_super[matched_columns].rename(
        columns=dict(zip(matched_columns, df_sub.columns))
    )
    df_super_matched = normalize_table(df_super_matched, question, query_super)

    try:
        assert_frame_equal(df_sub_normalized, df_super_matched, check_dtype=False)
        return True
    except AssertionError:
        return False


async def compare_query_results(
    query_gold: str,
    query_gen: str,
    df_gen: pd.DataFrame,
    question: str,
    db_type: str,
    db_creds: Dict[str, str],
) -> Dict[str, bool]:
    """
    Compares the results of two queries and returns a dictionary with the key:
    'correct' indicating if the queries are correct or if the result of the
    generated query is a subset of the golden query.
    Returns the error message in case of an error.
    """
    correct = False
    df_gold, err_msg = await execute_sql(db_type, db_creds, query_gold)
    # check if df_gold is an empty dataframe
    # this is because the function errors out when df_gold is empty
    if err_msg:
        LOGGER.error(err_msg)
        correct = False
    elif df_gold.empty and df_gen.empty:
        correct = False
    elif compare_df(df_gold, df_gen, question, query_gold, query_gen):
        correct = True
    elif subset_df(df_gold, df_gen, question, query_gen, query_gold):
        correct = True
    return {"correct": correct}


def add_schema_to_tables(query, schema):
    # Parse the query into a SQL AST (Abstract Syntax Tree)
    tree = parse_one(query)

    # Traverse and modify all table nodes in the AST
    for node in tree.find_all(exp.Table):
        # If the table node has a schema, skip it
        if node.catalog or node.db:
            continue
        # Modify the table name by prefixing it with the schema
        node.set("this", f"{schema}.{node.this}")

    # Return the modified SQL query as a string
    return tree.sql()


def add_hard_filters(sql: str, hard_filters: list[HardFilter]) -> str:
    """
    Takes in a SQL query and a list of HardFilter objects.
    For every SELECT that references a table_name from any HardFilter,
    add conditions (table_alias.column_name operator 'value') into the WHERE.
    """
    if not hard_filters or len(hard_filters) == 0:
        return sql
    
    # Parse into sqlglot Expression Tree
    parsed = parse_one(sql, read="postgres")

    # Map each SELECT node -> {table_name: set_of_aliases}
    select_table_aliases = {}

    def collect_tables(node, current_select=None):
        # If this node is a SELECT, mark it as the current SELECT
        if isinstance(node, exp.Select):
            current_select = node
            if current_select not in select_table_aliases:
                select_table_aliases[current_select] = {}

        # If this node is a table reference, record it in the current SELECT
        if isinstance(node, exp.Table):
            table_name = node.name  # e.g. 'my_table'
            alias = node.alias or table_name
            if current_select:
                select_table_aliases[current_select].setdefault(table_name, set()).add(alias)
        
        # Recurse into children
        for value in node.args.values():
            if isinstance(value, exp.Expression):
                collect_tables(value, current_select)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, exp.Expression):
                        collect_tables(item, current_select)

    collect_tables(parsed)

    def build_filter_expr(hf: HardFilter, alias: str) -> exp.Expression:
        """
        Build something like `alias.column_name = 'value'`.
        """
        col = exp.Column(
            this=exp.to_identifier(hf.column_name),
            table=exp.to_identifier(alias),
        )
        val = exp.Literal.string(hf.value)
        op_map = {
            "=":  exp.EQ,
            "!=": exp.NEQ,
            ">":  exp.GT,
            ">=": exp.GTE,
            "<":  exp.LT,
            "<=": exp.LTE,
        }
        op_class = op_map.get(hf.operator, exp.EQ)
        return op_class(this=col, expression=val)

    def apply_filters_to_select(select_node: exp.Select):
        """
        For a given SELECT node, gather *all* the filters that apply
        to any tables it references, and AND them all into the WHERE.
        """
        if select_node not in select_table_aliases:
            return

        table_map = select_table_aliases[select_node]
        # Example: table_map = {"my_table": {"t"}}

        # Build a list of all new conditions
        new_conds = []
        for table_name, aliases in table_map.items():
            # For each HardFilter that mentions `table_name`, build conditions
            for hf in hard_filters:
                if hf.table_name == table_name:
                    for alias in aliases:
                        new_conds.append(build_filter_expr(hf, alias))

        # If no new conditions, do nothing
        if not new_conds:
            return

        # Combine them into a single expression with AND
        # e.g. t.foo = 'bar' AND t.baz = 'qux' AND ...
        final_new_cond = new_conds[0]
        for cond in new_conds[1:]:
            final_new_cond = exp.And(this=final_new_cond, expression=cond)

        # Merge with existing WHERE
        existing_where = select_node.args.get("where")
        if existing_where:
            combined = exp.And(this=existing_where.this, expression=final_new_cond)
            select_node.set("where", exp.Where(this=combined))
        else:
            select_node.set("where", exp.Where(this=final_new_cond))

    def walk(node):
        # If it's a SELECT, apply all relevant filters at once
        if isinstance(node, exp.Select):
            apply_filters_to_select(node)

        # Recurse to children
        for k, v in node.args.items():
            if isinstance(v, exp.Expression):
                walk(v)
            elif isinstance(v, list):
                for x in v:
                    if isinstance(x, exp.Expression):
                        walk(x)

    # Walk the AST once, applying filters to each SELECT node
    walk(parsed)

    return parsed.sql(dialect="postgres")


def get_messages(
    db_type: str,
    date_today: str,
    instructions: str,
    user_question: str,
    table_metadata_ddl: str,
    system_prompt: str,
    user_prompt: str,
    previous_context: list[QuestionAnswer] | None = None,
    golden_queries_prompt: str = "",
):
    """
    Creates messages for the chatbot.
    """
    system_prompt = system_prompt.format(db_type=db_type, date_today=date_today)
    previous_messages = []
    if previous_context and len(previous_context) > 0:
        for question_answer in previous_context:
            previous_messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Create a SQL query for answering the following question: `{question_answer.question}`."
                        "Note that subsequent questions are a follow-on question from one, and you should keep this in mind when creating the query for future questions."
                    ),
                }
            )
            previous_messages.append(
                {
                    "role": "assistant",
                    "content": f"```sql\n{question_answer.answer};\n```",
                }
            )

    user_prompt = user_prompt.format(
        user_question=user_question,
        table_metadata_ddl=table_metadata_ddl,
        instructions=instructions,
        golden_queries_prompt=golden_queries_prompt,
    )

    messages = (
        [{"role": "system", "content": system_prompt}]
        + previous_messages
        + [{"role": "user", "content": user_prompt}]
    )
    for message in messages:
        LOGGER.debug(f"{message['role']}: {message['content']}")
    return messages


def clean_generated_query(query: str):
    """
    Clean up the generated query by
    - formatting the query using sqlparse
    - fixing common problems in LLM-powered query generation with post-processing heuristics

    KNOWN ISSUES: the division fix will only work with Postgres/Redshift/Snowflake/Databricks. It might not work with other databases.
    """

    query = sqlparse.format(query, reindent_aligned=True)

    # if the string `< =` is present, replace it with `<=`. Similarly for `> =` and `>=`
    query = query.replace("< =", "<=").replace("> =", ">=")

    # if the string ` / NULLIF (` is present, replace it with `/ NULLIF ( 1.0 * `.
    # This is a fix for ensuring that the denominator is always a float in division operations.
    query = query.replace("/ NULLIF (", "/ NULLIF (1.0 * ")
    return query


async def generate_sql_query(
    question: str, 
    db_name: str = None, 
    db_type: str = None, 
    metadata: list[ColumnMetadata] = None,
    instructions: str = None,
    previous_context: list[QuestionAnswer] = None,
    hard_filters: list[HardFilter] = None,
    num_golden_queries: int = 4,
    model_name: str = O3_MINI,
):
    """
    Generate SQL query for a given question, using an LLM.
    if db_type, metadata, and instructions are explicitly provided, they are used as is.
    Else, we use the db_name to extract the db_type, metadata, and instructions.
    Returns the generated SQL query and the error message if any.
    """
    t_start, timings = time.time(), []

    using_db_metadata = metadata is None or len(metadata) == 0

    if db_type is None:
        db_type, _ = await get_db_type_creds(db_name)
    t_start = save_timing(t_start, "Retrieved db type", timings)    
    
    if using_db_metadata:
        metadata = await get_metadata(db_name)
    t_start = save_timing(t_start, "Retrieved metadata", timings)

    if metadata is None or len(metadata) == 0:
        return {"error": "metadata is required"}
    
    if instructions is None:
        if using_db_metadata:
            instructions = await get_instructions(db_name)
    t_start = save_timing(t_start, "Retrieved instructions", timings)
    
    golden_queries_prompt = ""
    
    if using_db_metadata:
        question_embedding = await get_embedding(question)
        t_start = save_timing(t_start, "Embedded question", timings)

        golden_queries = await get_closest_golden_queries(
            db_name=db_name,
            question_embedding=question_embedding,
            num_queries=num_golden_queries,
        )
        t_start = save_timing(t_start, "Retrieved golden queries", timings)

        for i, golden_query in enumerate(golden_queries):
            golden_queries_prompt += f"Example question {i+1}: {golden_query.question}\nExample query {i+1}:\n```sql\n{golden_query.sql}\n```\n\n"
        
        if golden_queries_prompt != "":
            golden_queries_prompt = "The following are some potentially relevant questions and their corresponding SQL queries:\n\n" + golden_queries_prompt
    
    messages = get_messages(
        db_type=db_type,
        date_today=datetime.now().strftime("%Y-%m-%d"),
        instructions=instructions,
        user_question=question,
        table_metadata_ddl=mk_create_ddl(metadata),
        system_prompt=GENERATE_SQL_SYSTEM_PROMPT,
        user_prompt=GENERATE_SQL_USER_PROMPT,
        previous_context=previous_context,
        golden_queries_prompt=golden_queries_prompt,
    )

    query = await chat_async(
        model=model_name,
        messages=messages,
        # if model_name is a reasoning model, the temperature param will automatically be deleted in the request
        # else, we want to use temperature=0
        temperature=0.0,
        # for reasoning models, we want to use low reasoning effort
        # for non-reasoning models, this param will be ignored
        reasoning_effort="low",
    )

    LOGGER.info("latency of query generation in seconds: " + "{:.2f}".format(query.time) + "s")
    LOGGER.info(
        "cost of query in cents: " + "{:.2f}".format(query.cost_in_cents) + "¢"
    )

    sql_generated = query.content
    sql_generated = sql_generated.split("```sql", 1)[-1].split(";", 1)[0].replace("```", "").strip()
    sql_generated = add_hard_filters(sql_generated, hard_filters)
    sql_generated = clean_generated_query(sql_generated)
    
    log_timings(timings)

    if not safe_sql(sql_generated):
        LOGGER.error("Unsafe SQL query")
        LOGGER.info(sql_generated)
        response = {"sql": None, "error": "Unsafe SQL query"}
    else:
        response = {"sql": sql_generated, "error": None}

    return response


async def retry_query_after_error(
    question: str,
    sql: str = None,
    error: str = None,
    db_name: str = None,
    metadata: list[ColumnMetadata] = None,
    db_type: str = None,
) -> Optional[str]:
    """
    Fix the error that occurred while generating SQL / executing the query.
    Returns the fixed sql query if successful, else None.
    """
    if not db_type:
        db_type = await get_db_type(db_name)
    
    if not metadata or len(metadata) == 0:
        metadata = await get_metadata(db_name)
    
    if not metadata or len(metadata) == 0:
        LOGGER.error("No metadata found while fixing SQL query")
        return {
            "sql": None,
            "error": "No metadata found",
        }

    metadata_ddl = mk_create_ddl(metadata)

    system_prompt = FIX_SQL_SYSTEM_PROMPT.format(db_type=db_type)
    user_prompt = FIX_SQL_USER_PROMPT.format(
        db_type=db_type,
        sql=sql,
        error=error,
        question=question,
        table_metadata_ddl=metadata_ddl,
    )

    query = await chat_async(
        model=GPT_4O,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        prediction={
            "type": "content",
            "content": sql,
        }
    )
    LOGGER.info("Latency of query correction in seconds: " + "{:.2f}".format(query.time) + "s")
    LOGGER.info(
        "Cost of query correction in cents: " + "{:.2f}".format(query.cost_in_cents) + "¢"
    )
    
    sql_generated = query.content
    sql_generated = sql_generated.split("```sql", 1)[-1].split(";", 1)[0].replace("```", "").strip()
    sql_generated = clean_generated_query(sql_generated)

    if not safe_sql(sql_generated):
        LOGGER.error("Unsafe SQL query")
        LOGGER.info(sql_generated)
        return {
            "sql": None,
            "error": "Unsafe SQL query",
        }
    else:
        return {
            "sql": sql_generated,
            "error": None,
        }