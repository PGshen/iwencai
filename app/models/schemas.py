from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Literal, Union, List
from datetime import datetime


# ==================== Scrape Models ====================

class ScrapeRequest(BaseModel):
    """Request model for data scraping."""
    config_id: Optional[str] = Field(None, description="Use pre-configured scrape config")
    url: Optional[str] = Field(None, description="Target API URL")
    method: Literal["GET", "POST"] = Field("GET", description="HTTP method")
    headers: Optional[dict[str, str]] = Field(default_factory=dict, description="Request headers")
    params: Optional[dict[str, Any]] = Field(default_factory=dict, description="Query parameters")
    body: Optional[Any] = Field(None, description="Request body for POST (dict or string)")
    extract_type: Literal["python", "jsonpath"] = Field("python", description="How to extract data: python code or json path")
    json_path: Optional[str] = Field(None, description="JSON path to extract data (if extract_type is jsonpath)")
    parser_code: Optional[str] = Field(None, description="Python code to parse response (if extract_type is python)")
    proxies: Optional[dict[str, str]] = Field(default=None, description="HTTP proxies mapping, e.g., {'http': 'http://ip:port', 'https': 'http://ip:port'}")


class ScrapeResponse(BaseModel):
    """Response model for data scraping."""
    success: bool
    data: Optional[Any] = None
    raw_response: Optional[Any] = None
    error: Optional[str] = None


# ==================== Push Models ====================

class PushMessage(BaseModel):
    """Message content for push."""
    title: Optional[str] = None
    content: str
    type: Literal["text", "markdown", "card"] = "text"


class PushRequest(BaseModel):
    """Request model for message push."""
    channel: Optional[Literal["feishu", "discord"]] = None
    webhook_url: Optional[str] = Field(None, description="Webhook URL, or use pre-configured")
    config_id: Optional[str] = Field(None, description="Use pre-configured push config")
    config_name: Optional[str] = Field(None, description="Use pre-configured push config by unique name")
    message: Union[PushMessage, str]


class PushResponse(BaseModel):
    """Response model for message push."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


# ==================== Config Models ====================

class ScrapeConfigCreate(BaseModel):
    """Model for creating scrape configuration."""
    name: str
    url: str
    method: Literal["GET", "POST"] = "GET"
    headers: Optional[dict[str, str]] = Field(default_factory=dict)
    params: Optional[dict[str, Any]] = Field(default_factory=dict)
    body: Optional[Any] = None
    extract_type: Literal["python", "jsonpath"] = "python"
    json_path: Optional[str] = None
    parser_code: Optional[str] = None


class ScrapeConfigResponse(ScrapeConfigCreate):
    """Response model for scrape configuration."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class PushConfigCreate(BaseModel):
    """Model for creating push configuration."""
    name: str
    channel: Literal["feishu", "discord"]
    webhook_url: str


class PushConfigResponse(PushConfigCreate):
    """Response model for push configuration."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime

class ProxyConfigCreate(BaseModel):
    """Model for creating proxy configuration."""
    name: str
    ip: str
    port: int
    scheme: Literal["http", "https", "socks5"] = "http"
    enabled: bool = True

class ProxyConfigUpdate(ProxyConfigCreate):
    """Model for updating proxy configuration."""
    pass

class ProxyConfigResponse(ProxyConfigCreate):
    """Response model for proxy configuration."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


# ==================== Schedule Models ====================

class ScheduleCreate(BaseModel):
    """Model for creating scheduled task."""
    name: str
    cron_expression: str = Field(..., description="Cron expression, e.g., '0 9 * * *'")
    scrape_config_id: str
    push_config_id: Optional[str] = None
    enabled: bool = True


class ScheduleResponse(ScheduleCreate):
    """Response model for scheduled task."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    next_run_time: Optional[datetime] = None
    created_at: datetime


# ==================== Business Template Models ====================

class BusinessTemplateCreate(BaseModel):
    """Model for creating business template."""
    model_config = ConfigDict(extra='ignore')
    name: str = Field(..., description="Unique template name/ID")
    description: Optional[str] = Field(None, description="Template description")
    url: str = Field(..., description="Target API URL")
    method: Literal["GET", "POST"] = "GET"
    headers: Optional[dict[str, str]] = Field(default_factory=dict)
    default_params: Optional[dict[str, Any]] = Field(default_factory=dict)
    body_template: Optional[Any] = None
    extract_type: Literal["python", "jsonpath"] = "python"
    json_path: Optional[str] = None
    parser_code: Optional[str] = None
    param_schema: Optional[dict[str, Any]] = Field(None, description="Schema for user params")
    cookie_config_id: Optional[str] = Field(None, description="Associated cookie configuration ID")
    header_group_id: Optional[str] = Field(None, description="Associated header group ID")


class BusinessTemplateResponse(BusinessTemplateCreate):
    """Response model for business template."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class CookieConfigCreate(BaseModel):
    name: str
    cookie_text: str
    proxy_config_id: Optional[str] = None

class CookieConfigUpdate(CookieConfigCreate):
    pass

class CookieConfigResponse(CookieConfigCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime

class HeaderGroupConfigCreate(BaseModel):
    name: str
    headers: Optional[dict[str, str]] = Field(default_factory=dict)
    proxy_config_id: Optional[str] = None

class HeaderGroupConfigUpdate(HeaderGroupConfigCreate):
    pass

class HeaderGroupConfigResponse(HeaderGroupConfigCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class SimpleScrapeRequest(BaseModel):
    """Request model for simple/foolproof scraping."""
    template_name: str = Field(..., description="Business template name")
    params: Optional[dict[str, Any]] = Field(default_factory=dict, description="User parameters")


class SimpleScrapeResponse(BaseModel):
    """Response model for simple scraping."""
    success: bool
    template_name: str
    data: Optional[Any] = None
    error: Optional[str] = None


# ==================== Scrape History Models ====================

class ScrapeHistoryResponse(BaseModel):
    """Response model for scrape history."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    url: str
    method: str
    request_params: Optional[dict] = None
    request_headers: Optional[dict[str, str]] = None
    request_body: Optional[Any] = None
    api_request_headers: Optional[dict[str, str]] = None
    api_request_params: Optional[dict] = None
    api_request_body: Optional[Any] = None
    success: bool
    response_data: Optional[Any] = None
    raw_response: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime

class ScrapeHistoryPaginatedResponse(BaseModel):
    """Response model for paginated scrape history."""
    items: List[ScrapeHistoryResponse]
    total: int
    page: int
    size: int
    pages: int


# ==================== Batch Task Models ====================

class BatchTaskCreate(BaseModel):
    """Model for creating/updating batch run task."""
    name: str
    template_name: str
    concurrency: int = Field(1, ge=1, le=100)
    sleep_ms: int = Field(0, ge=0, le=600000)
    output_dir: str = Field(..., description="Directory to save each request result")
    csv_text: str = Field(..., description="CSV content where first row is header")
    save_fields: Optional[List[str]] = Field(default=None, description="Fields to save into output file")
    data_json_path: Optional[str] = Field(default=None, description="JSON path for data extraction")


class BatchTaskResponse(BatchTaskCreate):
    """Response model for batch task."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    created_at: datetime


class BatchTaskItemResponse(BaseModel):
    """Response model for batch task items."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    seq_no: str
    params: Optional[dict] = None
    status: str
    output_file: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# ==================== Workflow Template Models ====================

class WorkflowTemplateCreate(BaseModel):
    """Model for creating workflow template."""
    model_config = ConfigDict(extra='ignore')
    name: str
    description: Optional[str] = None
    definition: dict

class WorkflowTemplateResponse(WorkflowTemplateCreate):
    """Response model for workflow template."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime
