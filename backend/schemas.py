from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from typing import List, Any


class DataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=3306, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)
    database: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: bool = True


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(DataSourceBase):
    pass


class DataSourceResponse(DataSourceBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SQLExecuteRequest(BaseModel):
    datasource_id: int
    sql: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=1000)


class SQLExecuteResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    total_rows: int
    page: int
    page_size: int
    total_pages: int
    execution_time_ms: int


class TestConnectionRequest(BaseModel):
    name: str
    host: str
    port: int
    username: str
    password: str
    database: str


class AuditLogResponse(BaseModel):
    id: int
    datasource_id: int
    datasource_name: str
    sql_statement: str
    result_rows: int
    execution_time_ms: int
    executed_by: str
    status: str
    error_message: Optional[str] = None
    blocked: bool = False
    block_reason: Optional[str] = None
    executed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedAuditLogs(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RiskRuleBase(BaseModel):
    rule_type: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    pattern: str = Field(..., min_length=1)
    description: Optional[str] = None
    severity: str = Field(default="high", pattern="^(low|medium|high)$")
    is_active: bool = True


class RiskRuleCreate(RiskRuleBase):
    pass


class RiskRuleUpdate(RiskRuleBase):
    pass


class RiskRuleResponse(RiskRuleBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RiskCheckResultResponse(BaseModel):
    blocked: bool
    reasons: List[str]
    severity: str


class MaskingRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    column_pattern: str = Field(..., min_length=1)
    mask_type: str = Field(..., pattern="^(phone|id_card|salary|name|custom)$")
    keep_prefix: int = Field(default=0, ge=0)
    keep_suffix: int = Field(default=0, ge=0)
    mask_char: str = Field(default="*", max_length=10)
    description: Optional[str] = None
    is_active: bool = True


class MaskingRuleCreate(MaskingRuleBase):
    pass


class MaskingRuleUpdate(MaskingRuleBase):
    pass


class MaskingRuleResponse(MaskingRuleBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
