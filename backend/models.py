from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base


class DataSource(Base):
    __tablename__ = "datasources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=3306)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    database = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, nullable=False)
    datasource_name = Column(String(255), nullable=False)
    sql_statement = Column(Text, nullable=False)
    result_rows = Column(Integer, default=0)
    execution_time_ms = Column(Integer, default=0)
    executed_by = Column(String(255), default="anonymous")
    status = Column(String(50), default="success")
    error_message = Column(Text, nullable=True)
    blocked = Column(Boolean, default=False)
    block_reason = Column(Text, nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    pattern = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), default="high")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
