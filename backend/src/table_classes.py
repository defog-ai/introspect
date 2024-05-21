from sqlalchemy import (
    Column,
    Boolean,
    TIMESTAMP,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Docs(Base):
    __tablename__ = "defog_docs"
    doc_id = Column(Text, primary_key=True)
    doc_md = Column(Text)
    doc_blocks = Column(JSONB)
    editor_defog_blocks = Column(JSONB)
    api_key = Column(Text, primary_key=True)
    timestamp = Column(Text)
    username = Column(Text)
    doc_xml = Column(Text)
    doc_uint8 = Column(JSONB)
    doc_title = Column(Text)
    archived = Column(Boolean, default=False)


class RecentlyViewedDocs(Base):
    __tablename__ = "defog_recently_viewed_docs"
    api_key = Column(Text, primary_key=True)
    username = Column(Text, primary_key=True)
    recent_docs = Column(JSONB)


class Reports(Base):
    __tablename__ = "defog_reports"
    api_key = Column(Text, primary_key=True)
    email = Column(Text)
    timestamp = Column(Text)
    report_uuid = Column(Text)
    approaches = Column(JSONB)
    report_markdown = Column(Text)
    clarify = Column(JSONB)
    understand = Column(JSONB)
    gen_approaches = Column(JSONB)
    user_question = Column(Text)
    gen_report = Column(JSONB)
    report_id = Column(Text, primary_key=True)
    gen_steps = Column(JSONB)
    follow_up_analyses = Column(JSONB)
    parent_analyses = Column(JSONB)
    username = Column(Text)


class TableCharts(Base):
    __tablename__ = "defog_table_charts"
    data_csv = Column(JSONB)
    query = Column(Text)
    chart_images = Column(JSONB)
    sql = Column(Text)
    code = Column(Text)
    table_id = Column(Text, primary_key=True)
    tool = Column(JSONB)
    edited = Column(Boolean)
    error = Column(Text)
    reactive_vars = Column(JSONB)


class ToolRuns(Base):
    __tablename__ = "defog_tool_runs"
    tool_run_id = Column(Text, primary_key=True)
    step = Column(JSONB)
    outputs = Column(JSONB)
    tool_name = Column(Text)
    tool_run_details = Column(JSONB)
    error_message = Column(Text)
    edited = Column(Boolean)
    analysis_id = Column(Text)


class Toolboxes(Base):
    __tablename__ = "defog_toolboxes"
    api_key = Column(Text, primary_key=True)
    username = Column(Text, primary_key=True)
    toolboxes = Column(JSONB)


class Users(Base):
    __tablename__ = "defog_users"
    username = Column(Text, primary_key=True)
    hashed_password = Column(Text)
    token = Column(Text)
    user_type = Column(Text)
    csv_tables = Column(Text)
    is_premium = Column(Boolean)
    created_at = Column(TIMESTAMP)
    is_verified = Column(Boolean)


class Feedback(Base):
    __tablename__ = "defog_plans_feedback"
    api_key = Column(Text, primary_key=True)
    username = Column(Text, primary_key=True)
    user_question = Column(Text, primary_key=True)
    embedding = Column(Vector)
    comments = Column(JSONB)
    is_correct = Column(Boolean, nullable=False)
    analysis_id = Column(Text, primary_key=True)
    # metadata_ because  Attribute name 'metadata' is reserved when using the Declarative API.
    metadata_ = Column("metadata", Text, nullable=False)
    client_description = Column(Text)
    glossary = Column(Text)
    db_type = Column(Text, nullable=False)
