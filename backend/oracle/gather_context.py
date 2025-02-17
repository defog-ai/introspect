import asyncio
import json
import time
import traceback
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from db_config import INTERNAL_DB, engine
from db_models import OracleSources
from generic_utils import make_request
from oracle.celery_app import LOGGER
from oracle.constants import TaskType
from sqlalchemy import insert, select, update
from utils_imported_data import (
    IMPORTED_SCHEMA,
    get_source_type,
    update_imported_tables,
    update_imported_tables_db,
)
from utils_logging import save_and_log, save_timing
from oracle.guidelines_tasks import populate_default_guidelines_task
import os

DEFOG_BASE_URL = os.environ.get("DEFOG_BASE_URL", "https://api.defog.ai")

async def gather_context(
    api_key: str,
    report_id: str,
    task_type: TaskType,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
):
    """
    This function will gather the context for the report, by consolidating
    information from the glossary, metadata, and unstructured data sources,
    which are relevant to the question and metric_sql provided.

    One of the key side effects is that it will save the tables from the parsed
    sources into the database, creating new tables, and updating the metadata
    in the backend with the new metadata.

    Returns a dictionary with the following outputs:

    Always present across task types:
    - problem_statement: str. The summarized brief of the problem at hand to solve. first to be generated.
    - context: str. The context of the problem, described qualitatively. second to be generated.
    - issues: List[str]. A list of issues with the data. empty list returned if no issues present. last to be generated.

    Exploration task type:
    - data_overview: str. A brief overview of the data.

    Prediction task type:
    - target: str. The target variable to predict.
    - features: List[str]. A list of features to use for prediction.

    Optimization task type:
    - objective: str. The objective of the optimization.
    - constraints: List[str]. A list of constraints for the formulation.
    - variables: List[str]. A list of decision variables that the user can control.
    """
    ts, timings = time.time(), []
    LOGGER.debug(f"Gathering context for report {report_id}")
    user_question = inputs["user_question"]
    LOGGER.debug("Got the following sources:")
    sources = []
    for link in inputs["sources"]:
        source = {
            "link": link,
            "type": get_source_type(link),
        }
        sources.append(source)
        LOGGER.debug(f"{source}")
    if len(sources) > 0:
        json_data = {
            "api_key": api_key,
            "user_question": user_question,
            "sources": sources,
        }
        # each source now contains "text" and "summary" keys
        sources_parsed = await make_request(
            DEFOG_BASE_URL + "/unstructured_data/parse", json_data
        )
        sources_to_insert = []
        for source in sources_parsed:
            attributes = source.get("attributes")
            if isinstance(attributes, Dict) or isinstance(attributes, List):
                attributes = json.dumps(attributes)
            source_to_insert = {
                "link": source["link"],
                "title": source.get("title", ""),
                "position": source.get("position"),
                "source_type": source.get("type"),
                "attributes": attributes,
                "snippet": source.get("snippet"),
                "text_parsed": source.get("text"),
                "text_summary": source.get("summary"),
            }
            sources_to_insert.append(source_to_insert)
        async with AsyncSession(engine) as session:
            async with session.begin():
                # insert the sources into the database if not present. otherwise update
                for source in sources_to_insert:
                    stmt = select(OracleSources).where(OracleSources.link == source["link"])
                    result = await session.execute(stmt)
                    if result.scalar() is None:
                        source["api_key"] = api_key
                        stmt = insert(OracleSources).values(source)
                        await session.execute(stmt)
                        LOGGER.debug(f"Inserted source {source['link']} into the database.")
                    else:
                        stmt = (
                            update(OracleSources)
                            .where(OracleSources.link == source["link"])
                            .values(source)
                        )
                        await session.execute(stmt)
                        LOGGER.debug(f"Updated source {source['link']} in the database.")
        LOGGER.debug(f"Inserted {len(sources_to_insert)} sources into the database.")
        ts = save_timing(ts, "Sources parsed", timings)

        parse_table_tasks = []
        table_keys = []
        for source in sources_parsed:
            for i, table in enumerate(source.get("tables", [])):
                column_names = table.get("column_names")
                rows = table.get("rows")
                if not column_names or not rows:
                    LOGGER.error(
                        f"No column names or rows found in table {i}. Skipping table:\n{table}"
                    )
                    continue
                table_data = {
                    "api_key": api_key,
                    "all_rows": [table["column_names"]] + table["rows"],
                    "previous_text": table.get("previous_text"),
                }
                if table.get("table_page", None):
                    table_keys.append(
                        (source["link"], table["table_page"])
                    )  # use table page as index if available
                else:
                    table_keys.append((source["link"], i))
                parse_table_tasks.append(
                    make_request(
                        DEFOG_BASE_URL + "/unstructured_data/infer_table_properties",
                        table_data,
                    )
                )
        parsed_tables = await asyncio.gather(*parse_table_tasks)
        inserted_tables = {}

        for (link, table_index), parsed_table in zip(table_keys, parsed_tables):
            try:
                # input validation
                if "table_name" not in parsed_table:
                    LOGGER.error("No table name found in parsed table.")
                    continue
                table_name = parsed_table["table_name"]
                table_description = parsed_table.get("table_description", None)
                if "columns" not in parsed_table:
                    LOGGER.error(f"No columns found in parsed table `{table_name}`.")
                    continue
                columns = parsed_table["columns"]
                column_names = [column["column_name"] for column in columns]
                num_cols = len(column_names)
                if "rows" not in parsed_table:
                    LOGGER.error(f"No rows found in parsed table `{table_name}`.")
                    continue
                rows = parsed_table["rows"]  # 2D list of data
                # check data has correct number of columns passed for each row
                if not all(len(row) == num_cols for row in rows):
                    LOGGER.error(
                        f"Unable to insert table `{table_name}.` Data has mismatched number of columns for each row. Header has {len(data[0])} columns: {data[0]}, but data has {len(data[1])} columns: {data[1]}."
                    )
                    continue

                schema_table_name = f"{IMPORTED_SCHEMA}.{table_name}"
                # create the table and insert the data into imported_tables database, parsed schema
                data = [column_names] + rows
                success, old_table_name = update_imported_tables_db(
                    api_key, link, table_index, table_name, data, IMPORTED_SCHEMA
                )
                if not success:
                    LOGGER.error(
                        f"Failed to update imported tables database for table `{table_name}`."
                    )
                    continue
                # update the imported_tables table in internal db
                update_imported_tables(
                    api_key,
                    link,
                    table_index,
                    old_table_name,
                    schema_table_name,
                    table_description,
                )
                [
                    column.pop("fn", None) for column in columns
                ]  # remove "fn" key if present before updating metadata
                inserted_tables[schema_table_name] = columns
            except Exception as e:
                LOGGER.error(
                    f"Error occurred in parsing table: {e}\n{traceback.format_exc()}"
                )
        ts = save_timing(ts, "Tables saved", timings)
        # get and update metadata if inserted_tables is not empty
        if inserted_tables:
            response = await make_request(
                DEFOG_BASE_URL + "/get_metadata", {"api_key": api_key, "imported": True}
            )
            md = response.get("table_metadata", {}) if response else {}
            md.update(inserted_tables)
            response = await make_request(
                DEFOG_BASE_URL + "/update_metadata",
                {
                    "api_key": api_key,
                    "table_metadata": md,
                    "db_type": INTERNAL_DB,
                    "imported": True,
                },
            )
            if response.get("status") == "success":
                task = populate_default_guidelines_task.apply_async(
                    args=[api_key]
                )
                LOGGER.info(f"Scheduled populate_default_guidelines_task with id {task.id} for api_key {api_key}")
            LOGGER.info(f"Updated metadata for api_key {api_key}")
            ts = save_timing(ts, "Metadata updated", timings)
        else:
            LOGGER.info("No parsed tables to save.")
    else:
        sources_parsed = []
        LOGGER.info("No sources to parse.")

    answered_clarifications = []
    for clarification in inputs.get("clarifications", []):
        if (
            isinstance(clarification, dict)
            and "clarification" in clarification
            and "answer" in clarification
            and clarification["answer"]
        ):
            if type(clarification["answer"]) == list:
                answer = ", ".join(clarification["answer"])
            else:
                answer = str(clarification["answer"])
            answered_clarifications.append(
                {
                    "clarification": clarification["clarification"],
                    "answer": answer
                }
            )
    LOGGER.debug(f"Answered clarifications: {answered_clarifications}")

    # summarize all sources. we only need the title, type, and summary
    sources_summary = []
    for source in sources_parsed:
        source_summary = {
            "link": source.get("link"),
            "title": source.get("title", ""),
            "type": source.get("type"),
            "summary": source.get("summary"),
        }
        sources_summary.append(source_summary)
    json_data = {
        "api_key": api_key,
        "user_question": user_question,
        "task_type": task_type.value,
        "sources": sources_summary,
        "clarifications": answered_clarifications,
    }
    combined_summary = await make_request(
        DEFOG_BASE_URL + "/unstructured_data/combine_summaries", json_data
    )
    if "error" in combined_summary:
        LOGGER.error(
            f"Error occurred in combining summaries: {combined_summary['error']}"
        )
        return

    # validate response from backend
    if "problem_statement" not in combined_summary:
        LOGGER.error("No problem statement found in combined summary.")
    if "context" not in combined_summary:
        LOGGER.error("No context found in combined summary.")
    if "issues" not in combined_summary:
        LOGGER.error("No issues found in combined summary.")
    if task_type == TaskType.EXPLORATION:
        if "data_overview" not in combined_summary:
            LOGGER.error("No data overview found in combined summary.")
    # no need for prediction as we don't formulate the prediction problem during
    # the context gathering stage
    elif task_type == TaskType.OPTIMIZATION:
        if "objective" not in combined_summary:
            LOGGER.error("No objective found in combined summary.")
        if "constraints" not in combined_summary:
            LOGGER.error("No constraints found in combined summary.")
        if "variables" not in combined_summary:
            LOGGER.error("No variables found in combined summary.")
    combined_summary["sources"] = sources_summary
    LOGGER.debug(f"Context gathered for report {report_id}:\n{combined_summary}")
    save_and_log(ts, "Combined summary", timings)
    return combined_summary
