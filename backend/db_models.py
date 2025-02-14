import os

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    JSON,
    MetaData,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base

base_metadata = MetaData()
Base = declarative_base(metadata=base_metadata)

################################################################################
# This file should only contain the database models.
# All other files should import this file and use the models where required.
# This file should not import stateful objects like engines, sessions, etc. to
# avoid circular imports.
#
# We order the models based on the timing of their creation / usage in the
# product:
# 1. Users
# 2. Credentials for connecting to databases
# 3. Metadata of the user's database tables
# 4. Additional context (glossary, golden queries, etc.)
# 5. Analyses and tool runs from the agents ui
# 6. Oracle related tables
################################################################################


class Users(Base):
    """
    Represents the Users table.
    username is generally the email address of the user.
    hashed_password is hash(username, salt, password)
    token is what we use to authenticate the user for all user-related requests.
    created_at is the timestamp when the user was created.
    """

    __tablename__ = "defog_users"
    username = Column(Text, primary_key=True)
    hashed_password = Column(Text)
    token = Column(Text, nullable=False)
    created_at = Column(DateTime)


class DbCreds(Base):
    """
    Table to store the database credentials for the user.
    Each api_key is associated with a single user profile's database.
    Note that api_key/key_name is an orthogonal concept to username/token.
    TODO (DEF-720): rename api_key to key_name
    """

    __tablename__ = "defog_db_creds"
    api_key = Column(Text, primary_key=True)
    db_type = Column(Text)
    db_creds = Column(JSON)


class DefogMetadata(Base):
    """
    Table to store the metadata for the user.
    1 user's metadata is associated with 1 api_key.
    Every column in the user's metadata maps to a row in this table.
    """

    __tablename__ = "defog_metadata"
    api_key = Column(String(255), primary_key=True)
    table_name = Column(Text, primary_key=True)
    column_name = Column(Text, primary_key=True)
    data_type = Column(Text)
    column_description = Column(Text)

    __table_args__ = (Index("defog_metadata_api_key_idx", "api_key"),)


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
    db_type = Column(Text, nullable=False)


class UserHistory(Base):
    __tablename__ = "defog_user_history"
    username = Column(Text, primary_key=True)
    history = Column(JSON)


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
    general_comments = Column(Text, default=None)
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
