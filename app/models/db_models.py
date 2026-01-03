from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class ScrapeConfig(Base):
    """Database model for scrape configuration."""
    __tablename__ = "scrape_configs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    url = Column(Text, nullable=False)
    method = Column(String(10), default="GET")
    headers = Column(JSON, default=dict)
    params = Column(JSON, default=dict)
    body = Column(JSON, nullable=True)
    extract_type = Column(String(20), default="python")
    json_path = Column(Text, nullable=True)
    parser_code = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PushConfig(Base):
    """Database model for push configuration."""
    __tablename__ = "push_configs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    channel = Column(String(20), nullable=False)
    webhook_url = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Schedule(Base):
    """Database model for scheduled tasks."""
    __tablename__ = "schedules"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    scrape_config_id = Column(String(36), nullable=False)
    push_config_id = Column(String(36), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class BusinessTemplate(Base):
    """Database model for business scrape templates (simple mode)."""
    __tablename__ = "business_templates"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=False)
    method = Column(String(10), default="GET")
    headers = Column(JSON, default=dict)
    default_params = Column(JSON, default=dict)
    body_template = Column(JSON, nullable=True)
    extract_type = Column(String(20), default="python")
    json_path = Column(Text, nullable=True)
    parser_code = Column(Text, nullable=True)
    param_schema = Column(JSON, nullable=True)  # Describes user-providable params
    proxy_config_id = Column(String(36), nullable=True)
    cookie_config_id = Column(String(36), nullable=True)
    header_group_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ScrapeHistory(Base):
    """Database model for scrape history records."""
    __tablename__ = "scrape_history"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    template_id = Column(String(36), nullable=True)  # null if advanced mode
    template_name = Column(String(100), nullable=True)
    url = Column(Text, nullable=False)
    method = Column(String(10), nullable=False)
    request_params = Column(JSON, nullable=True)
    request_headers = Column(JSON, nullable=True)
    request_body = Column(JSON, nullable=True)
    api_request_headers = Column(JSON, nullable=True)
    api_request_params = Column(JSON, nullable=True)
    api_request_body = Column(JSON, nullable=True)
    success = Column(Boolean, nullable=False)
    response_data = Column(JSON, nullable=True)
    raw_response = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ProxyConfig(Base):
    """Database model for global proxy configuration."""
    __tablename__ = "proxy_configs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    ip = Column(String(100), nullable=False)
    port = Column(String(10), nullable=False)
    scheme = Column(String(20), default="http")  # http, https, socks5
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CookieConfig(Base):
    __tablename__ = "cookie_configs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    cookie_text = Column(Text, nullable=False)
    proxy_config_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class HeaderGroupConfig(Base):
    __tablename__ = "header_groups"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    headers = Column(JSON, default=dict)
    proxy_config_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WorkflowTemplate(Base):
    """Database model for workflow templates (composed business templates)."""
    __tablename__ = "workflow_templates"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    definition = Column(JSON, nullable=False, default=dict)  # workflow DSL definition
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class BatchTask(Base):
    """Database model for batch run tasks."""
    __tablename__ = "batch_tasks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    template_name = Column(String(100), nullable=False)
    concurrency = Column(String(10), nullable=False, default="1")  # store as str to keep schema simple
    sleep_ms = Column(String(10), nullable=False, default="0")
    output_dir = Column(Text, nullable=False)  # relative or absolute path
    csv_text = Column(Text, nullable=False)    # CSV content (header row + data rows)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed
    save_fields = Column(JSON, nullable=True)  # list of keys to save: success,error,data,raw_response,request
    data_json_path = Column(Text, nullable=True)  # if saving data, allow json path extraction
    created_at = Column(DateTime, server_default=func.now())


class BatchTaskItem(Base):
    """Per-request item for a batch task run list."""
    __tablename__ = "batch_task_items"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), nullable=False)
    seq_no = Column(String(10), nullable=False)  # store as str for simplicity
    params = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed, canceled
    output_file = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
