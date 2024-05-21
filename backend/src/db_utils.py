import torch
import json
import traceback
import datetime
import uuid
import pandas as pd
from regex import R
from sqlalchemy import (
    create_engine,
    select,
    text,
    update,
    insert,
    delete,
    Text,
    Boolean,
    JSON,
)
from sqlalchemy.ext.automap import automap_base
from agents.planner_executor.tool_helpers.core_functions import (
    execute_code,
)

from pgvector.psycopg2 import register_vector
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Session
import psycopg2
import yaml

from utils import embed_string, warn_str, YieldList

with open("/agents-python-server/.env.yaml", "r") as f:
    env = yaml.safe_load(f)

report_assets_dir = env["report_assets_dir"]

db_creds = {
    "user": env["user"],
    "password": env["password"],
    "host": env["host"],
    "port": env["port"],
    "database": env["database"],
}


connection_uri = f"postgresql+psycopg2://{db_creds['user']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['database']}"

engine = create_engine(
    connection_uri,
    pool_pre_ping=True,
)

Base = automap_base()
Base.prepare(engine, reflect=True)

Docs = Base.classes.defog_docs
RecentlyViewedDocs = Base.classes.defog_recently_viewed_docs
Reports = Base.classes.defog_reports
TableCharts = Base.classes.defog_table_charts
ToolRuns = Base.classes.defog_tool_runs
Toolboxes = Base.classes.defog_toolboxes
Tools = Base.classes.defog_tools
Users = Base.classes.defog_users
Feedback = Base.classes.defog_plans_feedback


free_tier_quota = 100


def initialise_report(user_question, api_key, username, custom_id=None, other_data={}):
    err = None
    timestamp = str(datetime.datetime.now())
    new_report_data = None

    try:
        """Create a new report in the defog_reports table"""
        # err_validate = validate_user(api_key)

        # if api_key == "" or api_key is None or not api_key or err_validate is not None:
        #     err = err_validate or "Your API Key is invalid."
        with engine.begin() as conn:
            if not custom_id or custom_id == "":
                report_id = str(uuid.uuid4())
            else:
                report_id = custom_id
            print("Creating new report with uuid: ", report_id)
            new_report_data = {
                "user_question": user_question,
                "timestamp": timestamp,
                "report_id": report_id,
                "api_key": api_key,
                "username": username,
            }
            if other_data is not None and type(other_data) is dict:
                new_report_data.update(other_data)

            conn.execute(insert(Reports).values(new_report_data))
            # if other data has parent_analyses, insert report_id into the follow_up_analyses column, which is an array, of all the parent analyses
            if (
                other_data is not None
                and type(other_data) is dict
                and other_data.get("parent_analyses") is not None
            ):
                for parent_analysis_id in other_data.get("parent_analyses"):
                    # get the parent analysis
                    parent_analysis = conn.execute(
                        select(Reports).where(Reports.report_id == parent_analysis_id)
                    ).fetchone()
                    if parent_analysis is not None:
                        parent_analysis = parent_analysis._mapping
                        # get the follow_up_analyses array
                        follow_up_analyses = (
                            parent_analysis.get("follow_up_analyses") or []
                        )
                        # add the report_id to the array
                        follow_up_analyses.append(report_id)
                        # update the row
                        conn.execute(
                            update(Reports)
                            .where(Reports.report_id == parent_analysis_id)
                            .values(follow_up_analyses=follow_up_analyses)
                        )
                    else:
                        print(
                            "Could not find parent analysis with id: ",
                            parent_analysis_id,
                        )

    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not create a new report."
        new_report_data = None
    finally:
        return err, new_report_data


def add_report_markdown(report_markdown, api_key, report_id):
    """Add report's markdown to defog_reports table"""
    try:
        with engine.begin() as conn:
            conn.execute(
                update(Reports)
                .where(Reports.report_id == report_id, Reports.api_key == api_key)
                .values(report_markdown=report_markdown)
            )

        return {"success": True}
    except Exception as e:
        traceback.print_exc()
        return {
            "success": False,
            "error_message": "Server error. Could not save report.",
        }


def validate_user(api_key):
    """Validate user's API key + checks if they have quota left"""
    # check if it exists in defog users
    err = None
    try:
        with engine.begin() as conn:
            rows = conn.execute(select(Users).where(Users.token == api_key).limit(1))

            if rows is None or rows.rowcount == 0:
                err = "Your API key seems to be invalid"

            row = rows.fetchone()

            if row is None or row.is_premium is None or not row.is_premium:
                err = "You need to be a paid user to use the agents feature."

            elif row.is_premium:
                err = None

    except Exception as e:
        print(e)
        traceback.print_exc()
        err = "Error validating your API key."
    finally:
        return err


def get_report_data(report_id):
    try:
        err = None
        report_data = {}

        if report_id == "" or not report_id:
            print(report_id == "")
            print(report_id is None)
            print(not report_id)
            err = "Could not find report. Are you sure you have the correct link?"

        elif report_id != "" and report_id is not None and report_id != "new":
            print("Looking for uuid: ", report_id)
            # try to fetch report_data data
            with engine.begin() as conn:
                rows = conn.execute(
                    select(Reports).where(Reports.report_id == report_id)
                )

                if rows.rowcount != 0:
                    #  7b2b3091-02d1-45d4-9210-e8d855118690
                    print("Found uuid: ", report_id)
                    row = rows.fetchone()
                    report_data = report_data_from_row(row)
                else:
                    err = (
                        "Could not find report. Are you sure you have the correct link?"
                    )

    except Exception as e:
        err = "Server error. Please contact us."
        report_data = None
        print(e)
        traceback.print_exc()

    finally:
        return err, report_data


async def update_report_data(
    report_id, request_type=None, new_data=None, replace=False, overwrite_key=None
):
    err = None
    request_types = [
        "clarify",
        "understand",
        "gen_approaches",
        "gen_steps",
        "gen_report",
        "user_question",
    ]
    try:
        # if new data is a list, filter out null elements
        # this can sometimes happen when the LLM server takes too long to respond etc.
        if type(new_data) == list:
            new_data = list(filter(None, new_data))

        if request_type is None or request_type not in request_types:
            err = "Incorrect request_type: " + request_type

        else:
            with engine.begin() as conn:
                register_vector(conn.connection)
                # first get the data
                rows = conn.execute(
                    select(Reports.__table__.columns[request_type]).where(
                        Reports.report_id == report_id
                    )
                )

                if rows.rowcount != 0:
                    row = rows.fetchone()
                    # print(row)
                    curr_data = getattr(row, request_type) or []
                    print("current data length ", len(curr_data))

                    # if new data is a list and we're not asked to replace, concat
                    # if new data is anything else, replace
                    if (
                        type(new_data) == list or type(new_data) == YieldList
                    ) and not replace:
                        if not overwrite_key or type(overwrite_key) != str:
                            curr_data = curr_data + new_data
                        # if there's an overwrite_key provided,
                        # then go through old data, and the new_data
                        # if the overwrite_key is found in the old data, replace it with the elements that exist new_data with the same overwrite_key
                        # if it's not found, just append the item to the end
                        else:
                            print(
                                "Overwriting data with overwrite_key: ", overwrite_key
                            )
                            replaced = 0
                            for i, item in enumerate(new_data):
                                found = False
                                for j, old_item in enumerate(curr_data):
                                    if old_item.get(overwrite_key) == item.get(
                                        overwrite_key
                                    ):
                                        curr_data[j] = item
                                        found = True
                                        replaced += 1
                                        break
                                if not found:
                                    curr_data.append(item)

                            print(
                                f"Replaced {replaced} items in {request_type} with overwrite_key: {overwrite_key}"
                            )
                            print(
                                "New length of ", request_type, " is ", len(curr_data)
                            )
                    else:
                        curr_data = new_data
                    print("writing to ", request_type, "in report id: ", report_id)
                    print("writing array of length: ", len(curr_data))
                    # insert back into reports table
                    # if the request type is user_question, we will also update the embedding
                    if request_type == "user_question":
                        cursor = conn.connection.cursor()
                        new_embedding = await embed_string(new_data)
                        cursor.execute(
                            "UPDATE defog_reports SET user_question = %s, embedding = %s WHERE report_id = %s",
                            (new_data, new_embedding, report_id),
                        )
                    else:
                        conn.execute(
                            update(Reports)
                            .where(Reports.report_id == report_id)
                            .values({request_type: curr_data})
                        )
                else:
                    err = "Report not found."
                    print("\n\n\n")
                    print(err)
                    print("\n\n\n")
                    raise ValueError(err)

    except Exception as e:
        err = str(e)
        print(e)
        traceback.print_exc()
    finally:
        return err


def report_data_from_row(row):
    rpt = None
    try:
        clarify = None if row.clarify is None else row.clarify
        understand = None if row.understand is None else row.understand
        gen_approaches = None if row.gen_approaches is None else row.gen_approaches
        gen_steps = None if row.gen_steps is None else row.gen_steps
        gen_report = row.gen_report or None
        report_markdown = row.report_markdown or ""
        parent_analyses = row.parent_analyses or []
        follow_up_analyses = row.follow_up_analyses or []

        # send only the ones that are not none.
        # we should have a better solution to this.
        rpt = {
            "user_question": row.user_question,
            "report_id": row.report_id,
            "timestamp": row.timestamp,
            "report_markdown": report_markdown,
            "parent_analyses": parent_analyses,
            "follow_up_analyses": follow_up_analyses,
        }

        if clarify is not None:
            rpt["clarify"] = {
                "success": True,
                "clarification_questions": clarify,
            }
        if understand is not None:
            rpt["understand"] = {
                "success": True,
                "understanding": understand,
            }
        if gen_approaches is not None:
            rpt["gen_approaches"] = {
                "success": True,
                "approaches": gen_approaches,
            }

        if gen_steps is not None:
            rpt["gen_steps"] = {
                "success": True,
                "steps": gen_steps,
            }
        if gen_report is not None:
            rpt["gen_report"] = {
                "success": True,
                "report_sections": gen_report,
            }

    except Exception as e:
        print(e)
        traceback.print_exc()
        rpt = None
    finally:
        return rpt


def get_all_reports(api_key):
    # get reports from the reports table
    err = None
    reports = []
    try:
        with engine.begin() as conn:
            # first get the data
            rows = conn.execute(select(Reports).where(Reports.api_key == api_key))
            if rows.rowcount != 0:
                rows = rows.fetchall()

                # reshape with "success = true"
                for row in rows:
                    rpt = report_data_from_row(row)
                    if rpt is not None:
                        reports.append(rpt)
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = "Something went wrong while fetching your reports. Please contact us."
        reports = None
    finally:
        return err, reports


async def add_to_recently_viewed_docs(username, api_key, doc_id, timestamp):
    try:
        print("Adding to recently viewed docs for user: ", username)
        with engine.begin() as conn:
            # add to recently accessed documents for this username
            # check if it exists
            rows = conn.execute(
                select(RecentlyViewedDocs)
                .where(RecentlyViewedDocs.username == username)
                .where(RecentlyViewedDocs.api_key == api_key)
            )

            if rows.rowcount != 0:
                print("Adding to recently viewed docs for user: ", username)
                # get the recent_docs array
                row = rows.fetchone()
                recent_docs = row.recent_docs or []
                # recent_docs is an array of arrays
                # each item is a [doc_id, timestamp]
                # check if doc_id is already in the array
                # if it is, update the timestamp
                # if not, add it to the array
                found = False
                for i, doc in enumerate(recent_docs):
                    if doc[0] == doc_id:
                        recent_docs[i][1] = timestamp
                        found = True
                        break

                if not found:
                    recent_docs.append([doc_id, timestamp])

                # update the row
                conn.execute(
                    update(RecentlyViewedDocs)
                    .where(RecentlyViewedDocs.username == username)
                    .where(RecentlyViewedDocs.api_key == api_key)
                    .values(recent_docs=recent_docs)
                )
            else:
                # create a new row
                conn.execute(
                    insert(RecentlyViewedDocs).values(
                        {
                            "api_key": api_key,
                            "username": username,
                            "recent_docs": [[doc_id, timestamp]],
                        }
                    )
                )
    except Exception as e:
        print(e)
        # traceback.print_exc()
        print("Could not add to recently viewed docs\n")


async def get_doc_data(doc_id, api_key, username, col_name="doc_blocks"):
    err = None
    timestamp = str(datetime.datetime.now())
    doc_data = None

    try:
        """Find the document with the id in the Docs table.
        If it doesn't exist, create one and return empty data."""
        # err_validate = validate_user(api_key)

        # if api_key == "" or api_key is None or not api_key or err_validate is not None:
        #     err = err_validate or "Your API Key is invalid."
        with engine.begin() as conn:
            # check if document exists
            rows = conn.execute(select(Docs).where(Docs.doc_id == doc_id))

            if rows.rowcount != 0:
                # document exists
                print("Found document with id: ", doc_id)
                row = rows.fetchone()
                doc_data = {
                    "doc_id": row.doc_id,
                    col_name: getattr(row, col_name),
                }

            else:
                # create a new document
                print("Creating new document with id: ", doc_id)
                doc_data = {
                    "doc_id": doc_id,
                    "doc_blocks": None,
                    "doc_xml": None,
                    "doc_uint8": None,
                    "username": username,
                }

                conn.execute(
                    insert(Docs).values(
                        {
                            "doc_id": doc_id,
                            "api_key": api_key,
                            "doc_blocks": None,
                            "doc_xml": None,
                            "doc_uint8": None,
                            "timestamp": timestamp,
                            "username": username,
                        }
                    )
                )

    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not create a new report."
        doc_data = None
    finally:
        return err, doc_data


async def delete_doc(doc_id):
    err = None
    try:
        with engine.begin() as conn:
            result = conn.execute(delete(Docs).where(Docs.doc_id == doc_id))

            if result.rowcount != 0:
                print("Deleted doc with id: ", doc_id)
            else:
                err = "Doc not found."
                print("\n\n\n")
                print(err)
                print("\n\n\n")
                raise ValueError(err)
    except Exception as e:
        err = str(e)
        print(e)
        traceback.print_exc()
    finally:
        return err


async def update_doc_data(doc_id, col_names=[], new_data={}):
    err = None
    if len(col_names) == 0 and len(new_data) == 0:
        return None

    try:
        with engine.begin() as conn:
            # first get the data
            rows = conn.execute(
                select(*[Docs.__table__.columns[c] for c in col_names]).where(
                    Docs.doc_id == doc_id
                )
            )

            if rows.rowcount != 0:
                print("Updating document with id: ", doc_id, "column: ", col_names)
                conn.execute(update(Docs).where(Docs.doc_id == doc_id).values(new_data))
            else:
                err = "Doc not found."
                print("\n\n\n")
                print(err)
                print("\n\n\n")
                raise ValueError(err)
    except Exception as e:
        err = str(e)
        print(e)
        traceback.print_exc()
    finally:
        return err


def create_table_chart(table_data):
    err = None
    if table_data is None or table_data.get("table_id") is None:
        return "Invalid table data"

    try:
        with engine.begin() as conn:
            print("Creating new table chart with id: ", table_data.get("table_id"))
            conn.execute(insert(TableCharts).values(table_data))

    except Exception as e:
        err = str(e)
        print(e)
        traceback.print_exc()
    finally:
        return err


async def update_table_chart_data(table_id, edited_table_data):
    err = None
    analysis = None
    updated_data = None

    if table_id is None:
        return "Invalid table data"

    try:
        with engine.begin() as conn:
            # check if exists.
            # if not, create
            rows = conn.execute(
                select(TableCharts).where(TableCharts.table_id == table_id)
            )

            if rows.rowcount == 0:
                err = "Invalid table id"
            else:
                # print(edited_table_data)
                print("Running table again...")

                # execute the new code
                err, analysis, updated_data = await execute_code(
                    edited_table_data["code"]
                )

                if err is None:
                    chart_images = []
                    if hasattr(updated_data, "kmc_plot_paths"):
                        chart_images = [
                            {"path": kmc_path, "type": "kmc"}
                            for kmc_path in updated_data.kmc_plot_paths
                        ]

                    updated_data = {
                        "data_csv": updated_data.to_csv(
                            float_format="%.3f", index=False
                        ),
                        "sql": edited_table_data.get("sql"),
                        "code": edited_table_data.get("code"),
                        "tool": edited_table_data.get("tool"),
                        "reactive_vars": (
                            updated_data.reactive_vars
                            if hasattr(updated_data, "reactive_vars")
                            else None
                        ),
                        "table_id": table_id,
                        "chart_images": chart_images,
                        "error": None,
                    }

                    # insert the data back into TableCharts table
                    print("writing to table chart, table id: ", table_id)
                    updated_data["edited"] = True

                    conn.execute(
                        update(TableCharts)
                        .where(TableCharts.table_id == table_id)
                        .values(updated_data)
                    )
                else:
                    print("Error: ", err)
    except Exception as e:
        err = str(e)
        analysis = None
        updated_data = None
        print(e)
        traceback.print_exc()
    finally:
        return err, analysis, updated_data


async def get_table_data(table_id):
    err = None
    table_data = None
    if table_id == "" or table_id is None or not table_id:
        return "Invalid table data", None

    try:
        with engine.begin() as conn:
            # check if document exists
            rows = conn.execute(
                select(TableCharts).where(TableCharts.table_id == table_id)
            )

            if rows.rowcount != 0:
                # document exists
                print("Found table with id: ", table_id)
                row = rows.fetchone()
                table_data = row._mapping

            else:
                err = "Table not found."

    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not find table."
        table_data = None
    finally:
        return err, table_data


async def get_all_docs(username):
    # get reports from the reports table
    err = None
    own_docs = []
    recently_viewed_docs = []
    try:
        """Get docs for a user from the defog_docs table"""
        # err_validate = validate_user(api_key)

        # if api_key == "" or api_key is None or not api_key or err_validate is not None:
        #     err = err_validate or "Your API Key is invalid."

        with engine.begin() as conn:
            # first get the data
            rows = conn.execute(
                select(
                    Docs.__table__.columns["doc_id"],
                    Docs.__table__.columns["doc_title"],
                    Docs.__table__.columns["timestamp"],
                    Docs.__table__.columns["archived"],
                ).where(Docs.username == username)
            )
            if rows.rowcount != 0:
                rows = rows.fetchall()

                for row in rows:
                    doc = row._mapping
                    own_docs.append(doc)

        # get recently viewed docs
        with engine.begin() as conn:
            # first get the data
            # merge recentlyvieweddocs with docs to get the user_question too
            # create an array of objects with doc_id, doc_title, timestamp, user_question
            rows = conn.execute(
                select(
                    RecentlyViewedDocs.__table__.columns["recent_docs"],
                ).where(RecentlyViewedDocs.username == username)
            )

            if rows.rowcount != 0:
                rows = rows.fetchall()

                for row in rows:
                    doc = row._mapping
                    for recent_doc in doc["recent_docs"]:
                        # get the doc data from the docs table
                        # this will skip docs that have been deleted because of the where clause
                        match = conn.execute(
                            select(
                                Docs.__table__.columns["doc_id"],
                                Docs.__table__.columns["doc_title"],
                                Docs.__table__.columns["timestamp"],
                                Docs.__table__.columns["username"],
                            ).where(Docs.doc_id == recent_doc[0])
                        ).fetchone()

                        if match:
                            recently_viewed_docs.append(
                                {
                                    "doc_id": match.doc_id,
                                    "doc_title": match.doc_title,
                                    # also return user who created this document
                                    "username": match.username,
                                    "timestamp": recent_doc[1],
                                }
                            )

    except Exception as e:
        print(e)
        traceback.print_exc()
        err = "Something went wrong while fetching your documents. Please contact us."
        own_docs = None
        recently_viewed_docs = None
    finally:
        return err, own_docs, recently_viewed_docs


async def get_all_analyses(api_key):
    # get reports from the reports table
    err = None
    analyses = []
    try:
        """Create a new report in the defog_reports table"""
        # err_validate = validate_user(api_key)

        # if api_key == "" or api_key is None or not api_key or err_validate is not None:
        #     err = err_validate or "Your API Key is invalid."

        with engine.begin() as conn:
            # first get the data
            rows = conn.execute(
                select(
                    *[
                        Reports.__table__.columns["report_id"],
                        Reports.__table__.columns["user_question"],
                    ]
                )
                .where(Reports.api_key == api_key)
                .where(Reports.report_id.contains("analysis"))
            )

            if rows.rowcount != 0:
                rows = rows.fetchall()

                for row in rows:
                    analyses.append(row._mapping)
    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not find analyses for the user."
        analyses = []
    finally:
        return err, analyses


async def get_toolboxes(username):
    # table is defog_agent_toolboxes
    # get all toolboxes available to a user using the username
    err = None
    toolboxes = []
    try:
        with engine.begin() as conn:
            rows = conn.execute(
                select(Toolboxes).where(Toolboxes.username == username)
            ).fetchall()

            for row in rows:
                row_dict = row._mapping

                if len(row_dict["toolboxes"]) == 0:
                    continue

                if row_dict["toolboxes"][0] == "*":
                    toolboxes = ["data-fetching", "stats", "plots", "cancer-survival"]
                    break

                else:
                    toolboxes += row_dict["toolboxes"]
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = "Could not fetch toolboxes for the user."
        toolboxes = []
    finally:
        return err, toolboxes


async def update_particular_step(analysis_id, tool_run_id, prop, new_val):
    if tool_run_id is None or prop is None or analysis_id is None:
        return "Invalid tool run data"

    # get the report data
    with engine.begin() as conn:
        analysis_data = conn.execute(
            select(Reports).where(Reports.report_id == analysis_id)
        ).fetchone()

        if analysis_data is not None:
            # copy row mapping
            report = analysis_data._mapping
            # update the property
            new_steps = report.gen_steps
            for step in new_steps:
                if step["tool_run_id"] == tool_run_id:
                    step[prop] = new_val
                    break

            # update the row
            conn.execute(
                update(Reports)
                .where(Reports.report_id == analysis_id)
                .values(gen_steps=new_steps)
            )


# skip_step_update helps us skip a step update when createing a new step
# we first run the tool, and only if it runs fully, we create a new step in the analysis.
async def store_tool_run(analysis_id, step, run_result, skip_step_update=False):
    try:
        insert_data = {
            "analysis_id": analysis_id,
            "tool_run_id": step["tool_run_id"],
            "tool_name": step["tool_name"],
            "step": step,
            "tool_run_details": {},
            "outputs": {},
            "error_message": run_result.get("error_message"),
            "edited": False,
        }
        # store everything but the "outputs" key in tool_run_details
        for k, v in run_result.items():
            if k != "outputs":
                insert_data["tool_run_details"][k] = v

        # we will store chart images right now
        files_to_store_in_gcs = []
        # feather files later
        files_for_rabbitmq_queue = []

        # could have been an error, if so, no outputs
        if "outputs" in run_result:
            for i, k in enumerate(step["outputs_storage_keys"]):
                # if output is a pandas df, convert to csv
                out = run_result["outputs"][i]
                data = out.get("data")
                chart_images = out.get("chart_images")
                reactive_vars = out.get("reactive_vars")
                analysis = out.get("analysis")

                insert_data["outputs"][k] = {}

                if data is not None and type(data) == type(pd.DataFrame()):
                    # save this dataset on local disk in feather format in report_dataset_dir/datasets
                    db_path = step["tool_run_id"] + "_output-" + k + ".feather"

                    # for sending to client, store max 1000 rows
                    if len(data) > 1000:
                        print(
                            warn_str(
                                "More than 1000 rows in output. Storing full db as feather, but sending only 1000 rows to client."
                            )
                        )

                    insert_data["outputs"][k]["data"] = data.head(1000).to_csv(
                        float_format="%.3f", index=False
                    )

                    # have to reset index for feather to work
                    data.reset_index(drop=True).to_feather(
                        report_assets_dir + "/datasets/" + db_path
                    )

                    # also store this in gcs
                    files_for_rabbitmq_queue.append(
                        report_assets_dir + "/datasets/" + db_path
                    )

                # check if it has reactive_vars
                if reactive_vars is not None:
                    insert_data["outputs"][k]["reactive_vars"] = reactive_vars

                # check if it has chart images
                if chart_images is not None:
                    insert_data["outputs"][k]["chart_images"] = chart_images
                    try:
                        # i fear some error here someday
                        files_to_store_in_gcs += [
                            report_assets_dir + "/" + img["path"]
                            for img in chart_images
                        ]
                    except Exception as e:
                        print(e)
                        traceback.print_exc()
                        print("Could not store chart images to gcs")

                # check if it has analysis
                if analysis is not None and analysis != "":
                    insert_data["outputs"][k]["analysis"] = analysis

            # add files to rabbitmq queue
            # if len(files_for_rabbitmq_queue) > 0:
            #     err = await add_files_to_rabbitmq_queue(files_for_rabbitmq_queue)
            #     if err is not None:
            #         print(error_str(err))

            # # store images to gcs now
            # if len(files_to_store_in_gcs) > 0:
            #     await store_files_to_gcs(files_to_store_in_gcs)

        with engine.begin() as conn:
            # first check if this tool run already exists
            rows = conn.execute(
                select(ToolRuns).where(ToolRuns.tool_run_id == step["tool_run_id"])
            ).fetchone()
            if rows is not None:
                # update the row
                conn.execute(
                    update(ToolRuns)
                    .where(ToolRuns.tool_run_id == step["tool_run_id"])
                    .values(insert_data)
                )
            else:
                conn.execute(insert(ToolRuns).values(insert_data))

            if not skip_step_update:
                # also update the error message in gen_steps in the reports table
                await update_particular_step(
                    analysis_id,
                    step["tool_run_id"],
                    "error_message",
                    run_result.get("error_message"),
                )

        return {"success": True, "tool_run_data": insert_data}
    except Exception as e:
        print(e)
        traceback.print_exc()
        print("Could not store tool run")
        return {"success": False, "error_message": str(e)}


async def get_tool_run(tool_run_id):
    error = None
    tool_run_data = None
    try:
        with engine.begin() as conn:
            rows = conn.execute(
                select(ToolRuns).where(ToolRuns.tool_run_id == tool_run_id)
            ).fetchall()

            if len(rows) == 0:
                return {"success": False, "error_message": "Tool run not found"}

            row = rows[0]
            tool_run_data = row._mapping
    except Exception as e:
        print(e)
        traceback.print_exc()
        print("Could not fetch tool run")
        tool_run_data = None
        error = str(e)
    finally:
        return error, tool_run_data


async def update_tool_run_data(analysis_id, tool_run_id, prop, new_val):
    """
    Update a single property of a tool run.
    """

    error = None
    new_data = None
    if tool_run_id is None or prop is None or analysis_id is None:
        return "Invalid tool run data"

    # if new_val is a pandas df, only print the shape and columns
    if type(new_val) == type(pd.DataFrame()):
        print(
            "Updating property: ", prop, " with value: ", new_val.shape, new_val.columns
        )
    else:
        print("Updating property: ", prop, " with value: ", new_val)

    try:
        with engine.begin() as conn:
            # get tool run data
            row = conn.execute(
                select(ToolRuns).where(ToolRuns.tool_run_id == tool_run_id)
            ).fetchone()
            if row is None:
                error = "Tool run not found"
                return error

            step = row._mapping.step

            if prop == "sql" or prop == "code_str" or prop == "analysis":
                # these exist in tool_run_details
                # copy row mapping
                tool_run_details = row._mapping.tool_run_details
                # update the property
                tool_run_details[prop] = new_val
                # also set edited to True
                # update the row
                conn.execute(
                    update(ToolRuns)
                    .where(ToolRuns.tool_run_id == tool_run_id)
                    .values(tool_run_details=tool_run_details, edited=True)
                )
            elif prop == "error_message":
                # update the row
                # probably after a re run, so set edited to false
                # tool_run_data also unfortunately has error message in it's "step"
                new_step = row._mapping.step
                new_step["error_message"] = new_val
                conn.execute(
                    update(ToolRuns)
                    .where(ToolRuns.tool_run_id == tool_run_id)
                    .values(error_message=new_val, edited=False, step=new_step)
                )
                # also remove errors from the steps in the report_data
                await update_particular_step(
                    analysis_id, tool_run_id, "error_message", new_val
                )

            elif prop == "inputs":
                # these exist in step
                # copy row mapping
                # update the property
                step[prop] = new_val
                # also set edited to True
                # update the row
                conn.execute(
                    update(ToolRuns)
                    .where(ToolRuns.tool_run_id == tool_run_id)
                    .values(step=step, analysis_id=analysis_id, edited=True)
                )
                # we should also update this in the defog_reports table in the gen_steps column
                await update_particular_step(
                    analysis_id, tool_run_id, "inputs", new_val
                )

            elif prop == "outputs":
                files_for_rabbitmq_queue = []
                # set edited to false because this is most probably after a re run
                # this will only be called if data_Fetcher was re run with a new sql.
                # all other tools re runs will use the store_tool_run function.
                # don't need to check for chart_images or reactive_vars
                for k in new_val:
                    # update the row
                    # save this dataset on local disk in feather format in report_dataset_dir/datasets
                    db_path = step["tool_run_id"] + "_output-" + k + ".feather"
                    data = new_val[k]["data"]

                    if data is not None and type(data) == type(pd.DataFrame()):
                        if len(data) > 1000:
                            print(
                                warn_str(
                                    "More than 1000 rows in output. Storing full db as feather, but sending only 1000 rows to client."
                                )
                            )

                        # for sending to client, store max 1000 rows
                        new_val[k]["data"] = data.head(1000).to_csv(
                            float_format="%.3f", index=False
                        )

                        # have to reset index for feather to work
                        data.reset_index(drop=True).to_feather(
                            report_assets_dir + "/datasets/" + db_path
                        )

                        # also store this in gcs

                        files_for_rabbitmq_queue.append(
                            report_assets_dir + "/datasets/" + db_path
                        )

                # add files to rabbitmq queue
                # if len(files_for_rabbitmq_queue) > 0:
                #     err = await add_files_to_rabbitmq_queue(files_for_rabbitmq_queue)
                #     if err is not None:
                #         print(error_str(err))

                conn.execute(
                    update(ToolRuns)
                    .where(ToolRuns.tool_run_id == tool_run_id)
                    .values(outputs=new_val, edited=False)
                )

            row = conn.execute(
                select(ToolRuns).where(ToolRuns.tool_run_id == tool_run_id)
            ).fetchone()

            if row is not None:
                new_data = dict(row._mapping)

        return {"success": True, "tool_run_data": new_data}
    except Exception as e:
        print(e)
        traceback.print_exc()
        print("Could not fetch tool run")
        error = str(e)
        return {"success": False, "error_message": str(e)}


def get_parent_analyses(parent_analyses=[]):
    err = None
    analyses = []
    try:
        with engine.begin() as conn:
            # first get the data
            rows = conn.execute(
                select(
                    *[
                        Reports.__table__.columns["report_id"],
                        Reports.__table__.columns["user_question"],
                    ]
                ).where(Reports.report_id.in_(parent_analyses))
            )

            if rows.rowcount != 0:
                rows = rows.fetchall()

                for row in rows:
                    analyses.append(row._mapping)
    except Exception as e:
        traceback.print_exc()
        print(e)
        err = "Could not find analyses for the user."
        analyses = []
    finally:
        return err, analyses


def get_db_conn():
    conn = psycopg2.connect(
        host=env["host"],
        dbname=env["database"],
        user=env["user"],
        password=env["password"],
        port=env["port"],
    )
    return conn


async def store_feedback(
    api_key,
    username,
    user_question,
    analysis_id,
    is_correct,
    comments,
    metadata,
    client_description,
    glossary,
    db_type,
):
    error = None
    did_overwrite = False
    try:
        qn_embedding = None
        # only embed if it's a correct plan
        if is_correct:
            print("Embedding question", user_question)
            # get embedding of question
            qn_embedding = await embed_string(user_question)

            if qn_embedding is None:
                raise ValueError("Could not embed the question.")

            print("Embedding done")

        print(qn_embedding)

        session = Session(engine)
        session.connection()
        with engine.connect() as conn:
            register_vector(conn.connection)
            cursor = conn.connection.cursor()
            # check if entry exists with this analysis_id
            cursor.execute(
                "SELECT * FROM defog_plans_feedback WHERE analysis_id = %s",
                (analysis_id,),
            )
            rows = cursor.fetchall()
            if len(rows) != 0:
                print("Feedback exists for this analysis_id. Updating...")
                # update the row
                cursor.execute(
                    """
                    UPDATE defog_plans_feedback
                    SET api_key = %s, username = %s, user_question = %s, embedding = %s, is_correct = %s, comments = %s, metadata = %s, client_description = %s, glossary = %s, db_type = %s
                    WHERE analysis_id = %s
                    """,
                    (
                        api_key,
                        username,
                        user_question,
                        qn_embedding,
                        is_correct,
                        # comments is a dict
                        json.dumps(comments),
                        metadata,
                        client_description,
                        glossary,
                        db_type,
                        analysis_id,
                    ),
                )
                did_overwrite = True
            else:
                print("Feedback does not exist for this analysis_id. Inserting...")
                cursor.execute(
                    """
                    INSERT INTO defog_plans_feedback (api_key, username, analysis_id, user_question, embedding, is_correct, comments, metadata, db_type, client_description, glossary)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        api_key,
                        username,
                        analysis_id,
                        user_question,
                        qn_embedding,
                        is_correct,
                        # comments is a dict
                        json.dumps(comments),
                        metadata,
                        db_type,
                        client_description,
                        glossary,
                    ),
                )
            conn.connection.commit()
    except Exception as e:
        print(e)
        traceback.print_exc()
        error = str(e)
        did_overwrite = False
    finally:
        return error, did_overwrite


def get_distinct_closest_user_questions(
    user_question_embedding, n_closest_questions, threshold=0.2, max_n=2
):
    # calculate all numpy tensors to torch tensors
    user_question_embedding = torch.tensor(user_question_embedding.reshape(1, -1))

    # n_closest_questions is sqlalchemy rows
    n_closest_questions = [
        {
            "user_question": x["user_question"],
            "embedding": torch.tensor(x["embedding"]),
            "analysis_id": x["analysis_id"],
        }
        for x in n_closest_questions
    ]

    # Initialize selected user_questions and their embeddings
    selected_user_questions = []
    selected_user_question_embeddings = []

    # Iterate through sorted user_questions
    for q in n_closest_questions:
        emb = q["embedding"]

        # Check if the example is distinct from previously selected user_questions
        if len(selected_user_question_embeddings) == 0:
            selected_user_questions.append(q)
            selected_user_question_embeddings.append(emb)
        else:
            # Calculate cosine distances between the example and all selected user_questions
            distances = 1 - torch.nn.functional.cosine_similarity(
                emb,
                torch.stack(selected_user_question_embeddings, dim=0),
            )
            print(distances, flush=True)
            # Check if the example is distinct from all selected user_questions
            if torch.all(distances > threshold):
                selected_user_questions.append(q)
                selected_user_question_embeddings.append(emb)

        print(
            "Currently number of selected user_questions:",
            len(selected_user_questions),
            flush=True,
        )

        # Stop if the desired number of user_questions is reached
        if len(selected_user_questions) == max_n:
            break

    return selected_user_questions


# get correct plans
async def get_similar_correct_plans(report_id, api_key):
    err = None
    similar_plans = []
    try:
        # use the feedback table to get similar correct plans
        # filter to where feedback is_correct is true
        # get the embedding column from the report_id
        # run the cosine distance function directly in the ORDER BY clause, as it cannot be stored as an alias
        # as a reminder, `<=>` is cosine distance, `<->` is L2 distance, and `<#>` is inner product
        with engine.connect() as conn:
            cur = conn.connection.cursor()
            user_question_embedding = None
            cur.execute(
                """
                SELECT embedding FROM defog_reports WHERE report_id = %s
                """,
                (report_id,),
            )
            rows = cur.fetchall()
            if len(rows) == 0:
                raise ValueError("Report not found.")

            user_question_embedding = rows[0][0]

            cur.execute(
                """
                SELECT user_question, analysis_id, embedding
                FROM defog_plans_feedback
                WHERE api_key = %s AND is_correct = TRUE
                ORDER BY (embedding <=> %s) LIMIT 10;
                """,
                (api_key, user_question_embedding),
            )

            rows = cur.fetchall()

            # convert rows to a list of dictionaries
            rows = [
                {"user_question": i[0], "analysis_id": i[1], "embedding": i[2]}
                for i in rows
            ]

            print("All close rows", [x["user_question"] for x in rows])

            # now get distinct
            results = get_distinct_closest_user_questions(user_question_embedding, rows)

            print("Distinct close rows", [x["user_question"] for x in results])

            # get all data for these analyses
            for plan in results:
                row = conn.execute(
                    select(Reports).where(Reports.report_id == plan["analysis_id"])
                ).fetchone()

                if row is not None:
                    similar_plans.append(
                        {
                            "user_question": row.user_question,
                            "plan": row.gen_steps,
                        }
                    )

    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err, similar_plans


def get_all_tools(user_question_embedding=None, max_n=10, mandatory_tools=[]):
    err = None
    tools = {}
    try:
        with engine.connect() as conn:
            register_vector(conn.connection)
            all_tools = conn.execute(select(Tools)).fetchall()
            # convert this to a dictionary without embedding
            all_tools = {
                tool.function_name: {
                    "tool_name": tool.tool_name,
                    "function_name": tool.function_name,
                    "description": tool.description,
                    "code": tool.code,
                    "toolbox": tool.toolbox,
                    "input_metadata": tool.input_metadata,
                    "output_metadata": tool.output_metadata,
                    "cannot_delete": tool.cannot_delete,
                    "cannot_disable": tool.cannot_disable,
                    "disabled": tool.disabled,
                }
                for tool in all_tools
            }

            if user_question_embedding is None:
                # if user_question_embedding is None, return all tools
                tools = all_tools
            else:
                # if user_question_embedding is not None, return max_n closest tools
                cursor = conn.connection.cursor()
                cursor.execute(
                    """
                    SELECT function_name
                    FROM defog_tools
                    ORDER BY (embedding <=> %s) LIMIT %s;
                    """,
                    (user_question_embedding, max_n),
                )

                pruned = cursor.fetchall()

                # make sure we have mandatory_tools
                for mando_tool in mandatory_tools:
                    tools[mando_tool] = all_tools[mando_tool]

                for selected_tool in pruned:
                    if selected_tool[0] not in tools:
                        tools[selected_tool[0]] = all_tools[selected_tool[0]]

    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
        tools = []
    finally:
        return err, tools


async def add_tool(
    tool_name,
    function_name,
    description,
    code,
    input_metadata,
    output_metadata,
    toolbox,
    cannot_delete=False,
    cannot_disable=False,
):
    err = None
    try:
        # insert into the tools table
        with engine.begin() as conn:
            register_vector(conn.connection)
            # first check if it exists
            rows = conn.execute(select(Tools).where(Tools.tool_name == tool_name))
            if rows.rowcount != 0:
                raise ValueError(f"Tool {tool_name} already exists.")
            else:
                embedding = await embed_string(tool_name + "-" + description)
                cursor = conn.connection.cursor()
                query = """
                    INSERT INTO defog_tools (
                        tool_name, function_name, code, description, embedding, toolbox, 
                        input_metadata, output_metadata, cannot_delete, cannot_disable, disabled
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                values = (
                    tool_name,
                    function_name,
                    code,
                    description,
                    embedding,
                    toolbox,
                    json.dumps(input_metadata),
                    json.dumps(output_metadata),
                    cannot_delete,
                    cannot_disable,
                    False,
                )
                cursor.execute(query, values)

    except ValueError as e:
        err = str(e)
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err


async def toggle_disable_tool(function_name):
    err = None
    try:
        with engine.begin() as conn:
            # check cannot_disable
            rows = conn.execute(
                select(Tools).where(Tools.function_name == function_name)
            ).fetchone()
            if rows is None:
                raise ValueError(f"Tool {function_name} does not exist.")
            elif rows.cannot_disable:
                raise ValueError(
                    f"Tool {function_name} cannot be disabled. Please contact admin."
                )
            else:
                conn.execute(
                    update(Tools)
                    .where(Tools.function_name == function_name)
                    .values(disabled=not Tools.disabled)
                )
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err


async def delete_tool(function_name):
    err = None
    try:
        with engine.begin() as conn:
            # also cannot_delete check
            rows = conn.execute(
                select(Tools).where(Tools.function_name == function_name)
            ).fetchone()
            if rows is None:
                raise ValueError(f"Tool {function_name} does not exist.")
            elif rows.cannot_delete:
                raise ValueError(
                    f"Tool {function_name} cannot be deleted. Please contact admin."
                )
            else:
                conn.execute(delete(Tools).where(Tools.function_name == function_name))
    except Exception as e:
        print(e)
        traceback.print_exc()
        err = str(e)
    finally:
        return err
