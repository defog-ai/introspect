from datetime import datetime
import enum
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    JSON,
    MetaData,
    Text,
    Enum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, mapped_column
from pgvector.sqlalchemy import Vector
from datetime import datetime

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


# USERS AND AUTHENTICATION
class Users(Base):
    """
    Represents the Users table.
    username is generally the email address of the user.
    hashed_password is hash(username, salt, password)
    token is what we use to authenticate the user for all user-related requests.
    created_at is the timestamp when the user was created.
    """

    __tablename__ = "users"
    username = Column(Text, primary_key=True)
    hashed_password = Column(Text)
    token = Column(Text, nullable=False)
    created_at = Column(DateTime)


# DATABASE DETAILS
class DbCreds(Base):
    """
    Table to store the database credentials for the user.
    Each db_name is associated with a single user profile's database.
    Note that db_name is an orthogonal concept to username/token.
    """

    __tablename__ = "db_creds"
    db_name = Column(Text, primary_key=True)
    db_type = Column(Text)
    db_creds = Column(JSON)


class Metadata(Base):
    """
    Table to store the metadata for the user.
    1 user's metadata is associated with 1 db_name.
    Every column in the user's metadata maps to a row in this table.
    """

    __tablename__ = "metadata"
    db_name = Column(Text, primary_key=True)
    table_name = Column(Text, primary_key=True)
    column_name = Column(Text, primary_key=True)
    data_type = Column(Text)
    column_description = Column(Text)

    __table_args__ = (Index("metadata_db_name_idx", "db_name"),)


class TableInfo(Base):
    """
    Stores 1 row per table. Currently only used for table descriptions, but
    could be extended to store other additional metadata in the future like
    sample rows, join hints, embeddings, table-specific sample queries, etc.
    """

    __tablename__ = "table_info"
    db_name = Column(Text, primary_key=True)
    table_name = Column(Text, primary_key=True)
    table_description = Column(Text)

    __table_args__ = (Index("table_info_db_name_idx", "db_name"),)


# This was formerly known as "glossary"
class Instructions(Base):
    __tablename__ = "instructions"
    db_name = Column(Text, primary_key=True)
    sql_instructions = Column(Text)
    join_hints = Column(JSONB)


class GoldenQueries(Base):
    __tablename__ = "golden_queries"
    db_name = Column(Text, primary_key=True)
    question = Column(Text, primary_key=True)
    sql = Column(Text)
    embedding = mapped_column(Vector())


class ImportedTables(Base):
    __tablename__ = "imported_tables"
    db_name = Column(Text, primary_key=True)
    table_link = Column(Text, primary_key=True)
    table_position = Column(Integer, primary_key=True)
    table_name = Column(Text)
    table_description = Column(Text)


# ANALYSIS DETAILS
class Analyses(Base):
    __tablename__ = "analyses"
    analysis_id = Column(Text, primary_key=True)
    user_question = Column(Text, default=None)
    db_name = Column(Text, nullable=False)
    timestamp = Column(DateTime)
    follow_up_analyses = Column(JSON)
    parent_analyses = Column(JSON)
    is_root_analysis = Column(Boolean, default=True)
    root_analysis_id = Column(Text)
    direct_parent_id = Column(Text)
    data = Column(JSON)


# USER HISTORY (for query data page)
class UserHistory(Base):
    __tablename__ = "user_history"
    username = Column(Text, primary_key=True)
    history = Column(JSON)


# ORACLE TABLES

class OracleGuidelines(Base):
    __tablename__ = "oracle_guidelines"
    db_name = Column(Text, primary_key=True)
    clarification_guidelines = Column(Text)
    generate_questions_guidelines = Column(Text)
    generate_questions_deeper_guidelines = Column(Text)
    generate_report_guidelines = Column(Text)

class ReportStatus(enum.Enum):
    INITIALIZED = "INITIALIZED"
    THINKING = "THINKING"
    ERRORED = "ERRORED"
    DONE = "DONE"

class OracleReports(Base):
    __tablename__ = "oracle_reports"
    report_id = Column(Integer, primary_key=True, autoincrement=True)
    report_name = Column(Text)
    created_ts = Column(DateTime, default=datetime.now)
    status = Column(Enum(ReportStatus), default=ReportStatus.INITIALIZED)
    db_name = Column(Text)
    inputs = Column(JSON)
    mdx = Column(Text)
    analyses = Column(JSON) # this is a list of analyses
    feedback = Column(Text, default=None)
    general_comments = Column(Text, default=None)
    comments = Column(JSON, default=None)
    thinking_steps = Column(JSON, default=None)


class OracleSources(Base):
    __tablename__ = "oracle_sources"
    db_name = Column(Text, primary_key=True)
    link = Column(Text, primary_key=True)
    title = Column(Text)
    position = Column(Integer)
    source_type = Column(Text)
    attributes = Column(Text)
    snippet = Column(Text)
    text_parsed = Column(Text)
    text_summary = Column(Text)


# CUSTOM TOOLS
class CustomTools(Base):
    """
    Stores custom tools defined by users that can be used alongside default analysis tools.
    Each tool has a unique nam.
    """
    __tablename__ = "custom_tools"
    tool_name = Column(Text, primary_key=True)
    tool_description = Column(Text)
    input_model = Column(Text)  # JSON schema for input validation
    tool_code = Column(Text)    # The actual Python code for the tool
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
