"""Database credential utility functions."""

import traceback
from typing import Dict, Tuple
from defog.query import async_execute_query_once
from sqlalchemy import delete, select, update, insert
from utils_md import get_metadata
from db_config import engine
from db_models import Project, PDFFiles
from utils_logging import LOGGER
from defog import Defog
import os
import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession

home_dir = os.path.expanduser("~")
defog_path = os.path.join(home_dir, ".defog")


async def get_db_type_creds(db_name: str) -> Tuple[str, Dict[str, str]] | None:
    async with engine.begin() as conn:
        row = await conn.execute(
            select(Project.db_type, Project.db_creds).where(Project.db_name == db_name)
        )
        row = row.fetchone()
    return row


async def get_db_names() -> list[str]:
    async with engine.begin() as conn:
        result = await conn.execute(select(Project.db_name))
        db_names = result.scalars().all()
    return db_names


async def update_db_type_creds(db_name, db_type, db_creds):
    async with engine.begin() as conn:
        # first, check if the record exists
        record = await conn.execute(select(Project).where(Project.db_name == db_name))

        record = record.fetchone()

        if record:
            await conn.execute(
                update(Project)
                .where(Project.db_name == db_name)
                .values(db_type=db_type, db_creds=db_creds)
            )
        else:
            await conn.execute(
                insert(Project).values(
                    db_name=db_name, db_type=db_type, db_creds=db_creds
                )
            )

    return True


async def validate_db_connection(db_type, db_creds):
    for k in ["api_key", "db_type"]:
        if isinstance(db_creds, dict) and k in db_creds:
            del db_creds[k]

    if db_type == "bigquery":
        db_creds["json_key_path"] = "./bq.json"

    sql_query = "SELECT 'test';"
    try:
        await async_execute_query_once(
            db_type,
            db_creds,
            sql_query,
        )
        return True
    except Exception as e:
        LOGGER.error(str(e))
        return False


async def get_db_info(db_name):
    res = await get_db_type_creds(db_name)
    if not res:
        raise Exception("No db creds found")
    try:
        db_type, db_creds = res
        defog = Defog(api_key=db_name, db_type=db_type, db_creds=db_creds)
        can_connect = await validate_db_connection(db_type, db_creds)
        table_names = []

        if can_connect:
            table_names = await asyncio.to_thread(
                defog.generate_db_schema,
                tables=[],
                upload=False,
                scan=False,
                return_tables_only=True,
            )

        db_type = defog.db_type
        db_creds = defog.db_creds

        # get selected_tables from file. this is a legacy way of keeping track
        # of tables that the user has selected to add to the metadata
        # ideally we'd want this to be stored somewhere more persistent like in
        # the database, but we just keep it around for now to avoid breaking changes
        selected_tables_path = os.path.join(defog_path, f"selected_tables_{db_name}.json")
        if os.path.exists(selected_tables_path):
            with open(selected_tables_path, "r") as f:
                selected_tables_saved = json.load(f)
                if isinstance(selected_tables_saved, list):
                    selected_tables = selected_tables_saved
                else:
                    selected_tables = table_names
        else:
            selected_tables = table_names

        metadata = await get_metadata(db_name)
        
        # Get associated PDF files
        associated_files = await get_project_associated_files(db_name)

        return {
            "db_name": db_name,
            "tables": table_names,
            "db_creds": db_creds,
            "db_type": db_type,
            "selected_tables": selected_tables,
            "can_connect": can_connect,
            "metadata": metadata,
            "associated_files": associated_files
        }
    except Exception as e:
        LOGGER.error(f"Error getting DB info: {str(e)}")
        return {
            "db_name": db_name,
            "can_connect": False,
            "tables": [],
            "db_creds": {},
            "db_type": None,
            "selected_tables": [],
            "metadata": [],
            "associated_files": []
        }


async def delete_db_info(db_name):
    async with engine.begin() as conn:
        await conn.execute(delete(Project).where(Project.db_name == db_name))
        
        
async def get_project_associated_files(db_name):
    """
    Get file information associated with a project.
    Returns a list of dictionaries with file_id and file_name for each associated file.
    """
    pdf_files = []
    
    try:
        async with AsyncSession(engine) as session:
            project = await session.execute(
                select(Project).where(Project.db_name == db_name)
            )
            project = project.scalar_one_or_none()

            if not project:
                return []

            if not project.associated_files:
                return []

        
            associated_files = project.associated_files

            # Get file names for associated files
            pdf_files = await session.execute(
                select(PDFFiles).where(
                    PDFFiles.file_id.in_(associated_files)
                )
            )
            pdf_files = pdf_files.scalars().all()
            pdf_files = [{"file_id": row.file_id, "file_name": row.file_name} for row in pdf_files]
    except Exception as e:
        traceback.print_exc()
        LOGGER.error(f"Error getting associated files: {str(e)}")
        
    return pdf_files
