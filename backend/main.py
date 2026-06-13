from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import time
import math
import re

from database import engine, get_db, Base
import models
import schemas
import sql_risk

Base.metadata.create_all(bind=engine)

app = FastAPI(title="数据库查询审计系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_mysql_connection(host, port, username, password, database):
    try:
        import pymysql
        conn = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=3,
            read_timeout=5,
            write_timeout=5
        )
        return conn
    except ImportError:
        raise HTTPException(status_code=500, detail="pymysql未安装")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接失败: {str(e)}")


def is_select_query(sql):
    trimmed = sql.strip().lstrip('(').strip()
    first_word = re.split(r'\s+', trimmed, maxsplit=1)[0].upper()
    return first_word in ('SELECT', 'WITH')


def has_limit_clause(sql):
    pattern = re.compile(r'\bLIMIT\b', re.IGNORECASE)
    return bool(pattern.search(sql))


def remove_trailing_semicolon(sql):
    return sql.rstrip().rstrip(';').rstrip()


def execute_query_with_pagination(conn, sql, page, page_size):
    import pymysql.cursors
    try:
        with conn.cursor() as cursor:
            clean_sql = remove_trailing_semicolon(sql)
            is_select = is_select_query(clean_sql)
            has_limit = has_limit_clause(clean_sql)

            if is_select and not has_limit:
                count_sql = f"SELECT COUNT(*) as total FROM ({clean_sql}) AS _count_wrapper"
                cursor.execute(count_sql)
                total_rows = cursor.fetchone()["total"]

                offset = (page - 1) * page_size
                paginated_sql = f"{clean_sql} LIMIT {page_size} OFFSET {offset}"
                cursor.execute(paginated_sql)
            else:
                cursor.execute(clean_sql)
                total_rows = cursor.rowcount

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            rows_list = [[row[col] for col in columns] for row in rows]

            if is_select and not has_limit:
                total_pages = math.ceil(total_rows / page_size) if total_rows > 0 else 0
            else:
                total_pages = 1 if total_rows > 0 else 0

            return columns, rows_list, total_rows, total_pages
    except Exception as e:
        raise e


@app.get("/")
def read_root():
    return {"message": "数据库查询审计系统 API", "version": "1.0.0"}


@app.get("/api/datasources", response_model=list[schemas.DataSourceResponse])
def list_datasources(db: Session = Depends(get_db)):
    return db.query(models.DataSource).order_by(models.DataSource.id.desc()).all()


@app.get("/api/datasources/{ds_id}", response_model=schemas.DataSourceResponse)
def get_datasource(ds_id: int, db: Session = Depends(get_db)):
    ds = db.query(models.DataSource).filter(models.DataSource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return ds


@app.post("/api/datasources", response_model=schemas.DataSourceResponse)
def create_datasource(data: schemas.DataSourceCreate, db: Session = Depends(get_db)):
    ds = models.DataSource(**data.model_dump())
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


@app.put("/api/datasources/{ds_id}", response_model=schemas.DataSourceResponse)
def update_datasource(ds_id: int, data: schemas.DataSourceUpdate, db: Session = Depends(get_db)):
    ds = db.query(models.DataSource).filter(models.DataSource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    for key, value in data.model_dump().items():
        setattr(ds, key, value)
    db.commit()
    db.refresh(ds)
    return ds


@app.delete("/api/datasources/{ds_id}")
def delete_datasource(ds_id: int, db: Session = Depends(get_db)):
    ds = db.query(models.DataSource).filter(models.DataSource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    db.delete(ds)
    db.commit()
    return {"message": "删除成功"}


@app.post("/api/datasources/test")
def test_connection(data: schemas.TestConnectionRequest):
    try:
        conn = get_mysql_connection(
            host=data.host,
            port=data.port,
            username=data.username,
            password=data.password,
            database=data.database
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        conn.close()
        return {"success": True, "message": "连接成功"}
    except HTTPException as e:
        return {"success": False, "message": e.detail}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/execute", response_model=schemas.SQLExecuteResponse)
def execute_sql(data: schemas.SQLExecuteRequest, db: Session = Depends(get_db)):
    ds = db.query(models.DataSource).filter(models.DataSource.id == data.datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    risk_rules = db.query(models.RiskRule).filter(
        models.RiskRule.is_active == True,
        models.RiskRule.rule_type == "sensitive_table"
    ).all()

    risk_result = sql_risk.run_risk_check(data.sql, risk_rules)

    start_time = time.time()
    conn = None
    try:
        if risk_result.blocked:
            block_reason_str = "; ".join(risk_result.reasons)
            execution_time_ms = int((time.time() - start_time) * 1000)
            audit_log = models.AuditLog(
                datasource_id=ds.id,
                datasource_name=ds.name,
                sql_statement=data.sql,
                result_rows=0,
                execution_time_ms=execution_time_ms,
                status="blocked",
                blocked=True,
                block_reason=block_reason_str,
                error_message=f"SQL 风险拦截: {block_reason_str}"
            )
            db.add(audit_log)
            db.commit()
            raise HTTPException(status_code=403, detail=f"SQL 风险拦截: {block_reason_str}")

        conn = get_mysql_connection(
            host=ds.host,
            port=ds.port,
            username=ds.username,
            password=ds.password,
            database=ds.database
        )
        columns, rows_list, total_rows, total_pages = execute_query_with_pagination(
            conn,
            data.sql.strip().rstrip(';'),
            data.page,
            data.page_size
        )
        execution_time_ms = int((time.time() - start_time) * 1000)

        warning_reason = "; ".join(risk_result.reasons) if risk_result.reasons else None
        audit_log = models.AuditLog(
            datasource_id=ds.id,
            datasource_name=ds.name,
            sql_statement=data.sql,
            result_rows=total_rows,
            execution_time_ms=execution_time_ms,
            status="success",
            blocked=False,
            block_reason=warning_reason
        )
        db.add(audit_log)
        db.commit()

        resp = schemas.SQLExecuteResponse(
            columns=columns,
            rows=rows_list,
            total_rows=total_rows,
            page=data.page,
            page_size=data.page_size,
            total_pages=total_pages,
            execution_time_ms=execution_time_ms
        )
        return resp
    except HTTPException:
        raise
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        audit_log = models.AuditLog(
            datasource_id=ds.id,
            datasource_name=ds.name,
            sql_statement=data.sql,
            result_rows=0,
            execution_time_ms=execution_time_ms,
            status="failed",
            blocked=False,
            error_message=str(e)
        )
        db.add(audit_log)
        db.commit()
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


@app.get("/api/audit-logs", response_model=schemas.PaginatedAuditLogs)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    datasource_id: Optional[int] = None,
    status: Optional[str] = None,
    blocked: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.AuditLog)
    if datasource_id:
        query = query.filter(models.AuditLog.datasource_id == datasource_id)
    if status:
        query = query.filter(models.AuditLog.status == status)
    if blocked is not None:
        query = query.filter(models.AuditLog.blocked == blocked)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    items = query.order_by(models.AuditLog.id.desc()).offset(offset).limit(page_size).all()

    return schemas.PaginatedAuditLogs(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@app.delete("/api/audit-logs/{log_id}")
def delete_audit_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(models.AuditLog).filter(models.AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    db.delete(log)
    db.commit()
    return {"message": "删除成功"}


@app.get("/api/risk-rules", response_model=list[schemas.RiskRuleResponse])
def list_risk_rules(
    rule_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.RiskRule)
    if rule_type:
        query = query.filter(models.RiskRule.rule_type == rule_type)
    if is_active is not None:
        query = query.filter(models.RiskRule.is_active == is_active)
    return query.order_by(models.RiskRule.id.desc()).all()


@app.get("/api/risk-rules/{rule_id}", response_model=schemas.RiskRuleResponse)
def get_risk_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(models.RiskRule).filter(models.RiskRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule


@app.post("/api/risk-rules", response_model=schemas.RiskRuleResponse)
def create_risk_rule(data: schemas.RiskRuleCreate, db: Session = Depends(get_db)):
    if data.rule_type == "sensitive_table":
        try:
            import re
            re.compile(data.pattern)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"正则表达式无效: {str(e)}")
    rule = models.RiskRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@app.put("/api/risk-rules/{rule_id}", response_model=schemas.RiskRuleResponse)
def update_risk_rule(rule_id: int, data: schemas.RiskRuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(models.RiskRule).filter(models.RiskRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    if data.rule_type == "sensitive_table":
        try:
            import re
            re.compile(data.pattern)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"正则表达式无效: {str(e)}")
    for key, value in data.model_dump().items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


@app.delete("/api/risk-rules/{rule_id}")
def delete_risk_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(models.RiskRule).filter(models.RiskRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()
    return {"message": "删除成功"}


@app.post("/api/risk-check", response_model=schemas.RiskCheckResultResponse)
def check_sql_risk(data: schemas.SQLExecuteRequest, db: Session = Depends(get_db)):
    risk_rules = db.query(models.RiskRule).filter(
        models.RiskRule.is_active == True,
        models.RiskRule.rule_type == "sensitive_table"
    ).all()
    result = sql_risk.run_risk_check(data.sql, risk_rules)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8099)
