from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, Text
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.declarative import declarative_base
from db_config import metadata, ORACLE_ENABLED, imported_tables_engine

Base = declarative_base(metadata=metadata)

class Analyses(Base):
    __tablename__ = "defog_analyses"
    analysis_id = Column(Text, primary_key=True)
    api_key = Column(Text, nullable=False)
    email = Column(Text)
    timestamp = Column(DateTime)
    clarify = Column(JSON)
    assignment_understanding = Column(JSON)
    user_question = Column(Text)
    gen_steps = Column(JSON)
    follow_up_analyses = Column(JSON)
    parent_analyses = Column(JSON)
    is_root_analysis = Column(Boolean, default=True)
    root_analysis_id = Column(Text)
    direct_parent_id = Column(Text)
    username = Column(Text)

class TableCharts(Base):
    __tablename__ = "defog_table_charts"
    table_id = Column(Text, primary_key=True)
    data_csv = Column(JSON)
    query = Column(Text)
    chart_images = Column(JSON)
    sql = Column(Text)
    code = Column(Text)
    tool = Column(JSON)
    edited = Column(Integer)
    error = Column(Text)
    reactive_vars = Column(JSON)

class ToolRuns(Base):
    __tablename__ = "defog_tool_runs"
    tool_run_id = Column(Text, primary_key=True)
    step = Column(JSON)
    outputs = Column(JSON)
    tool_name = Column(Text)
    tool_run_details = Column(JSON)
    error_message = Column(Text)
    edited = Column(Integer)
    analysis_id = Column(Text)

class Tools(Base):
    __tablename__ = "defog_tools"
    tool_name = Column(Text, primary_key=True)
    function_name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    input_metadata = Column(JSON)
    output_metadata = Column(JSON)
    toolbox = Column(Text, default=None)
    disabled = Column(Boolean, default=False)
    cannot_delete = Column(Boolean, default=False)
    cannot_disable = Column(Boolean, default=False)

class Users(Base):
    __tablename__ = "defog_users"
    username = Column(Text, primary_key=True)
    hashed_password = Column(Text)
    token = Column(Text, nullable=False)
    user_type = Column(Text, nullable=False)
    created_at = Column(DateTime)

class PlansFeedback(Base):
    __tablename__ = "defog_plans_feedback"
    analysis_id = Column(Text, primary_key=True)
    api_key = Column(Text, nullable=False)
    user_question = Column(Text, nullable=False)
    username = Column(Text, nullable=False)
    comments = Column(JSON)
    is_correct = Column(Boolean, nullable=False)
    feedback_metadata = Column(Text, name="metadata", nullable=False)
    client_description = Column(Text)
    glossary = Column(Text)

class DbCreds(Base):
    __tablename__ = "defog_db_creds"
    api_key = Column(Text, primary_key=True)
    db_type = Column(Text)
    db_creds = Column(JSON)

class UserHistory(Base):
    __tablename__ = "defog_user_history"
    username = Column(Text, primary_key=True)
    history = Column(JSON)

if ORACLE_ENABLED:
    class OracleGuidelines(Base):
        __tablename__ = "oracle_guidelines"
        api_key = Column(Text, primary_key=True)
        clarification_guidelines = Column(Text)
        generate_questions_guidelines = Column(Text)
        generate_questions_deeper_guidelines = Column(Text)
        generate_report_guidelines = Column(Text)

    class OracleReports(Base):
        __tablename__ = "oracle_reports"
        report_id = Column(Integer, primary_key=True, autoincrement=True)
        report_name = Column(Text)
        status = Column(Text)
        created_ts = Column(DateTime)
        api_key = Column(Text)
        username = Column(Text)
        inputs = Column(JSON)
        outputs = Column(JSON)
        feedback = Column(Text)
        comments = Column(JSON, default=None)

    class OracleAnalyses(Base):
        __tablename__ = "oracle_analyses"
        api_key = Column(Text, primary_key=True)
        report_id = Column(Integer, primary_key=True)
        analysis_id = Column(Text, primary_key=True)
        status = Column(Text, default="pending")
        analysis_json = Column(JSON)
        mdx = Column(Text, default=None)

    class OracleSources(Base):
        __tablename__ = "oracle_sources"
        api_key = Column(Text, primary_key=True)
        link = Column(Text, primary_key=True)
        title = Column(Text)
        position = Column(Integer)
        source_type = Column(Text)
        attributes = Column(Text)
        snippet = Column(Text)
        text_parsed = Column(Text)
        text_summary = Column(Text)

    class ImportedTables(Base):
        __tablename__ = "imported_tables"
        api_key = Column(Text, primary_key=True)
        table_link = Column(Text, primary_key=True)
        table_position = Column(Integer, primary_key=True)
        table_name = Column(Text)
        table_description = Column(Text)

    # Set up imported tables base
    try:
        ImportedTablesBase = automap_base()
        ImportedTablesBase.prepare(autoload_with=imported_tables_engine)
        ImportedTablesBase.classes.imported_tables = ImportedTables
    except Exception as e:
        from utils_logging import LOGGER
        LOGGER.debug(f"Error loading oracle tables: {e}")
