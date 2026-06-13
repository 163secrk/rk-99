from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import time
import math
import re

from database import engine, get_db, Base
import models
import schemas
import sql_risk
import masking
import sql_rollback

SECRET_KEY = "your-secret-key-change-in-production-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

Base.metadata.create_all(bind=engine)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return user


def require_role(allowed_roles: list):
    def role_checker(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return role_checker


def init_default_admin(db: Session):
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        admin = models.User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            role="dba",
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    dev = db.query(models.User).filter(models.User.username == "developer").first()
    if not dev:
        dev = models.User(
            username="developer",
            password_hash=get_password_hash("dev123456"),
            role="developer",
            is_active=True
        )
        db.add(dev)
        db.commit()
        db.refresh(dev)


with Session(bind=engine) as init_db:
    init_default_admin(init_db)

app = FastAPI(title="数据库查询审计系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/register", response_model=schemas.TokenResponse)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = models.User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        role="developer",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return schemas.TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=schemas.UserResponse.model_validate(user)
    )


@app.post("/api/login", response_model=schemas.TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return schemas.TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=schemas.UserResponse.model_validate(user)
    )


@app.get("/api/me", response_model=schemas.UserResponse)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.get("/api/users", response_model=list[schemas.UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    return db.query(models.User).order_by(models.User.id.desc()).all()


@app.post("/api/users", response_model=schemas.UserResponse)
def create_user_by_admin(
    data: schemas.UserCreateByAdmin,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    existing_user = db.query(models.User).filter(models.User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = models.User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        role=data.role,
        is_active=data.is_active
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.put("/api/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password is not None:
        user.password_hash = get_password_hash(data.password)
    db.commit()
    db.refresh(user)
    return user


@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    db.delete(user)
    db.commit()
    return {"message": "删除成功"}


@app.get("/api/my-logs", response_model=schemas.PaginatedAuditLogs)
def list_my_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.AuditLog).filter(models.AuditLog.executed_by == current_user.username)
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
def list_datasources(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.DataSource).order_by(models.DataSource.id.desc()).all()


@app.get("/api/datasources/{ds_id}", response_model=schemas.DataSourceResponse)
def get_datasource(
    ds_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    ds = db.query(models.DataSource).filter(models.DataSource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return ds


@app.post("/api/datasources", response_model=schemas.DataSourceResponse)
def create_datasource(
    data: schemas.DataSourceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    ds = models.DataSource(**data.model_dump())
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


@app.put("/api/datasources/{ds_id}", response_model=schemas.DataSourceResponse)
def update_datasource(
    ds_id: int,
    data: schemas.DataSourceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    ds = db.query(models.DataSource).filter(models.DataSource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    for key, value in data.model_dump().items():
        setattr(ds, key, value)
    db.commit()
    db.refresh(ds)
    return ds


@app.delete("/api/datasources/{ds_id}")
def delete_datasource(
    ds_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    ds = db.query(models.DataSource).filter(models.DataSource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    db.delete(ds)
    db.commit()
    return {"message": "删除成功"}


@app.post("/api/datasources/test")
def test_connection(
    data: schemas.TestConnectionRequest,
    current_user: models.User = Depends(require_role(["dba"]))
):
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
def execute_sql(
    data: schemas.SQLExecuteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    ds = db.query(models.DataSource).filter(models.DataSource.id == data.datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    risk_rules = db.query(models.RiskRule).filter(
        models.RiskRule.is_active == True,
        models.RiskRule.rule_type == "sensitive_table"
    ).all()

    risk_result = sql_risk.run_risk_check(data.sql, risk_rules)

    is_write = sql_rollback.is_write_operation(data.sql)
    if is_write and current_user.role != "dba":
        raise HTTPException(
            status_code=403,
            detail="写操作（INSERT/UPDATE/DELETE等）需要提交工单审批，请在工单模块中创建变更工单"
        )

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
                executed_by=current_user.username,
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
            executed_by=current_user.username,
            status="success",
            blocked=False,
            block_reason=warning_reason
        )
        db.add(audit_log)
        db.commit()

        masking_rules = db.query(models.MaskingRule).filter(
            models.MaskingRule.is_active == True
        ).all()

        if masking_rules:
            columns, rows_list = masking.apply_masking(columns, rows_list, masking_rules)

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
            executed_by=current_user.username,
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
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
def delete_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    query = db.query(models.RiskRule)
    if rule_type:
        query = query.filter(models.RiskRule.rule_type == rule_type)
    if is_active is not None:
        query = query.filter(models.RiskRule.is_active == is_active)
    return query.order_by(models.RiskRule.id.desc()).all()


@app.get("/api/risk-rules/{rule_id}", response_model=schemas.RiskRuleResponse)
def get_risk_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    rule = db.query(models.RiskRule).filter(models.RiskRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule


@app.post("/api/risk-rules", response_model=schemas.RiskRuleResponse)
def create_risk_rule(
    data: schemas.RiskRuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
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
def update_risk_rule(
    rule_id: int,
    data: schemas.RiskRuleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
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
def delete_risk_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    rule = db.query(models.RiskRule).filter(models.RiskRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()
    return {"message": "删除成功"}


@app.post("/api/risk-check", response_model=schemas.RiskCheckResultResponse)
def check_sql_risk(
    data: schemas.SQLExecuteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    risk_rules = db.query(models.RiskRule).filter(
        models.RiskRule.is_active == True,
        models.RiskRule.rule_type == "sensitive_table"
    ).all()
    result = sql_risk.run_risk_check(data.sql, risk_rules)
    return result


@app.get("/api/masking-rules", response_model=list[schemas.MaskingRuleResponse])
def list_masking_rules(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    query = db.query(models.MaskingRule)
    if is_active is not None:
        query = query.filter(models.MaskingRule.is_active == is_active)
    return query.order_by(models.MaskingRule.id.desc()).all()


@app.get("/api/masking-rules/{rule_id}", response_model=schemas.MaskingRuleResponse)
def get_masking_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    rule = db.query(models.MaskingRule).filter(models.MaskingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="脱敏规则不存在")
    return rule


@app.post("/api/masking-rules", response_model=schemas.MaskingRuleResponse)
def create_masking_rule(
    data: schemas.MaskingRuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    try:
        re.compile(data.column_pattern)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"列名匹配正则表达式无效: {str(e)}")
    rule = models.MaskingRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@app.put("/api/masking-rules/{rule_id}", response_model=schemas.MaskingRuleResponse)
def update_masking_rule(
    rule_id: int,
    data: schemas.MaskingRuleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    rule = db.query(models.MaskingRule).filter(models.MaskingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="脱敏规则不存在")
    try:
        re.compile(data.column_pattern)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"列名匹配正则表达式无效: {str(e)}")
    for key, value in data.model_dump().items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


@app.delete("/api/masking-rules/{rule_id}")
def delete_masking_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    rule = db.query(models.MaskingRule).filter(models.MaskingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="脱敏规则不存在")
    db.delete(rule)
    db.commit()
    return {"message": "删除成功"}


@app.get("/api/work-orders", response_model=schemas.PaginatedSqlWorkOrders)
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    datasource_id: Optional[int] = None,
    mine: Optional[bool] = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.SqlWorkOrder)
    if status:
        query = query.filter(models.SqlWorkOrder.status == status)
    if datasource_id:
        query = query.filter(models.SqlWorkOrder.datasource_id == datasource_id)
    if mine:
        query = query.filter(models.SqlWorkOrder.created_by == current_user.username)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    items = query.order_by(models.SqlWorkOrder.id.desc()).offset(offset).limit(page_size).all()

    return schemas.PaginatedSqlWorkOrders(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@app.get("/api/work-orders/{order_id}", response_model=schemas.SqlWorkOrderResponse)
def get_work_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    order = db.query(models.SqlWorkOrder).filter(models.SqlWorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="工单不存在")
    return order


@app.post("/api/work-orders", response_model=schemas.SqlWorkOrderResponse)
def create_work_order(
    data: schemas.SqlWorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    ds = db.query(models.DataSource).filter(models.DataSource.id == data.datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    if not sql_rollback.is_write_operation(data.sql_statement):
        raise HTTPException(status_code=400, detail="只有写操作（INSERT/UPDATE/DELETE等）需要提交工单审批，查询语句可直接执行")

    risk_rules = db.query(models.RiskRule).filter(
        models.RiskRule.is_active == True,
        models.RiskRule.rule_type == "sensitive_table"
    ).all()

    risk_result = sql_risk.run_risk_check(data.sql_statement, risk_rules)
    if risk_result.blocked:
        raise HTTPException(status_code=403, detail=f"SQL风险检查不通过: {'; '.join(risk_result.reasons)}")

    order = models.SqlWorkOrder(
        title=data.title,
        description=data.description,
        datasource_id=data.datasource_id,
        datasource_name=ds.name,
        sql_statement=data.sql_statement,
        status="pending",
        created_by=current_user.username
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@app.put("/api/work-orders/{order_id}", response_model=schemas.SqlWorkOrderResponse)
def update_work_order(
    order_id: int,
    data: schemas.SqlWorkOrderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    order = db.query(models.SqlWorkOrder).filter(models.SqlWorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="工单不存在")

    if order.created_by != current_user.username and current_user.role != "dba":
        raise HTTPException(status_code=403, detail="只能修改自己创建的工单")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="只有待审批状态的工单可以修改")

    if data.title is not None:
        order.title = data.title
    if data.description is not None:
        order.description = data.description
    if data.sql_statement is not None:
        if not sql_rollback.is_write_operation(data.sql_statement):
            raise HTTPException(status_code=400, detail="只有写操作需要提交工单审批")
        order.sql_statement = data.sql_statement

    db.commit()
    db.refresh(order)
    return order


@app.delete("/api/work-orders/{order_id}")
def delete_work_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    order = db.query(models.SqlWorkOrder).filter(models.SqlWorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="工单不存在")

    if order.created_by != current_user.username and current_user.role != "dba":
        raise HTTPException(status_code=403, detail="只能删除自己创建的工单")

    if order.status not in ["pending", "rejected"]:
        raise HTTPException(status_code=400, detail="只能删除待审批或已拒绝的工单")

    db.delete(order)
    db.commit()
    return {"message": "删除成功"}


@app.post("/api/work-orders/{order_id}/approve", response_model=schemas.SqlWorkOrderResponse)
def approve_work_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    order = db.query(models.SqlWorkOrder).filter(models.SqlWorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="工单不存在")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="只有待审批状态的工单可以审批")

    order.status = "approved"
    order.approved_by = current_user.username
    order.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(order)
    return order


@app.post("/api/work-orders/{order_id}/reject", response_model=schemas.SqlWorkOrderResponse)
def reject_work_order(
    order_id: int,
    data: schemas.SqlWorkOrderReject,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    order = db.query(models.SqlWorkOrder).filter(models.SqlWorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="工单不存在")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="只有待审批状态的工单可以拒绝")

    order.status = "rejected"
    order.rejected_by = current_user.username
    order.rejected_at = datetime.utcnow()
    order.reject_reason = data.reject_reason

    db.commit()
    db.refresh(order)
    return order


@app.post("/api/work-orders/{order_id}/execute", response_model=schemas.SqlWorkOrderResponse)
def execute_work_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    order = db.query(models.SqlWorkOrder).filter(models.SqlWorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="工单不存在")

    if order.status != "approved":
        raise HTTPException(status_code=400, detail="只有已审批通过的工单可以执行")

    ds = db.query(models.DataSource).filter(models.DataSource.id == order.datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    conn = None
    try:
        conn = get_mysql_connection(
            host=ds.host,
            port=ds.port,
            username=ds.username,
            password=ds.password,
            database=ds.database
        )

        rollback_sql = _generate_rollback_with_data(conn, order.sql_statement)
        order.rollback_sql = rollback_sql

        with conn.cursor() as cursor:
            statements = sql_rollback._split_statements(sql_rollback._strip_sql_comments(order.sql_statement))
            total_affected = 0
            for stmt in statements:
                if stmt.strip():
                    cursor.execute(stmt)
                    total_affected += cursor.rowcount
            conn.commit()

        order.status = "executed"
        order.executed_by = current_user.username
        order.executed_at = datetime.utcnow()
        order.execution_result = f"执行成功，影响 {total_affected} 行"
        order.affected_rows = total_affected

        audit_log = models.AuditLog(
            datasource_id=ds.id,
            datasource_name=ds.name,
            sql_statement=order.sql_statement,
            result_rows=total_affected,
            execution_time_ms=0,
            executed_by=current_user.username,
            status="success",
            blocked=False,
            block_reason=f"工单执行 #{order.id}"
        )
        db.add(audit_log)

        db.commit()
        db.refresh(order)
        return order

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        order.status = "approved"
        order.execution_error = str(e)
        db.commit()
        db.refresh(order)
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


@app.post("/api/work-orders/{order_id}/rollback", response_model=schemas.SqlWorkOrderResponse)
def rollback_work_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["dba"]))
):
    order = db.query(models.SqlWorkOrder).filter(models.SqlWorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="工单不存在")

    if order.status != "executed":
        raise HTTPException(status_code=400, detail="只有已执行的工单可以回滚")

    if not order.rollback_sql:
        raise HTTPException(status_code=400, detail="没有找到回滚SQL，无法回滚")

    ds = db.query(models.DataSource).filter(models.DataSource.id == order.datasource_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    conn = None
    try:
        conn = get_mysql_connection(
            host=ds.host,
            port=ds.port,
            username=ds.username,
            password=ds.password,
            database=ds.database
        )

        with conn.cursor() as cursor:
            statements = sql_rollback._split_statements(sql_rollback._strip_sql_comments(order.rollback_sql))
            total_affected = 0
            for stmt in statements:
                stmt = stmt.strip()
                if stmt and not stmt.startswith('--'):
                    cursor.execute(stmt)
                    total_affected += cursor.rowcount
            conn.commit()

        order.status = "rollbacked"
        order.rollbacked_by = current_user.username
        order.rollbacked_at = datetime.utcnow()
        order.rollback_result = f"回滚成功，影响 {total_affected} 行"

        audit_log = models.AuditLog(
            datasource_id=ds.id,
            datasource_name=ds.name,
            sql_statement=order.rollback_sql,
            result_rows=total_affected,
            execution_time_ms=0,
            executed_by=current_user.username,
            status="success",
            blocked=False,
            block_reason=f"工单回滚 #{order.id}"
        )
        db.add(audit_log)

        db.commit()
        db.refresh(order)
        return order

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        order.rollback_error = str(e)
        db.commit()
        db.refresh(order)
        raise HTTPException(status_code=500, detail=f"回滚失败: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def _generate_rollback_with_data(conn, sql: str) -> str:
    sql_clean = sql_rollback._strip_sql_comments(sql)
    statements = sql_rollback._split_statements(sql_clean)

    rollback_parts = []

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue

        first_kw = sql_rollback._get_first_keyword(stmt)

        if first_kw == 'INSERT':
            table = sql_rollback._extract_table_name(stmt, 'INSERT')
            columns, values = sql_rollback._extract_insert_columns_values(stmt)
            if table and columns and values:
                where_conditions = []
                for i, col in enumerate(columns):
                    if i < len(values):
                        where_conditions.append(f"{col} = {values[i]}")
                where_clause = ' AND '.join(where_conditions)
                rollback_parts.append(f"DELETE FROM {table} WHERE {where_clause}")

        elif first_kw == 'UPDATE':
            table = sql_rollback._extract_table_name(stmt, 'UPDATE')
            where_clause = sql_rollback._extract_where_clause(stmt)
            if table and where_clause:
                try:
                    with conn.cursor() as cursor:
                        query_sql = f"SELECT * FROM {table} WHERE {where_clause}"
                        cursor.execute(query_sql)
                        old_rows = cursor.fetchall()
                        if old_rows:
                            for row in old_rows:
                                set_parts = []
                                where_parts = []
                                for col, val in row.items():
                                    if val is None:
                                        set_parts.append(f"{col} = NULL")
                                    elif isinstance(val, (int, float)):
                                        set_parts.append(f"{col} = {val}")
                                    else:
                                        escaped_val = str(val).replace("'", "''")
                                        set_parts.append(f"{col} = '{escaped_val}'")
                                set_clause = ', '.join(set_parts)
                                pk_where = _build_primary_key_where(conn, table, row)
                                if pk_where:
                                    rollback_parts.append(f"UPDATE {table} SET {set_clause} WHERE {pk_where}")
                                else:
                                    rollback_parts.append(f"UPDATE {table} SET {set_clause} WHERE {where_clause} LIMIT 1")
                        else:
                            rollback_parts.append(f"-- 没有找到旧数据，跳过: {stmt[:50]}...")
                except Exception as e:
                    rollback_parts.append(f"-- 查询旧数据失败: {str(e)}")

        elif first_kw == 'DELETE':
            table = sql_rollback._extract_table_name(stmt, 'DELETE')
            where_clause = sql_rollback._extract_where_clause(stmt)
            if table and where_clause:
                try:
                    with conn.cursor() as cursor:
                        query_sql = f"SELECT * FROM {table} WHERE {where_clause}"
                        cursor.execute(query_sql)
                        old_rows = cursor.fetchall()
                        if old_rows:
                            for row in old_rows:
                                columns = []
                                values = []
                                for col, val in row.items():
                                    columns.append(col)
                                    if val is None:
                                        values.append('NULL')
                                    elif isinstance(val, (int, float)):
                                        values.append(str(val))
                                    else:
                                        escaped_val = str(val).replace("'", "''")
                                        values.append(f"'{escaped_val}'")
                                cols_str = ', '.join(columns)
                                vals_str = ', '.join(values)
                                rollback_parts.append(f"INSERT INTO {table} ({cols_str}) VALUES ({vals_str})")
                        else:
                            rollback_parts.append(f"-- 没有找到旧数据，跳过: {stmt[:50]}...")
                except Exception as e:
                    rollback_parts.append(f"-- 查询旧数据失败: {str(e)}")
        else:
            rollback_parts.append(f"-- 无法生成回滚SQL: {stmt[:80]}...")

    return ';\n'.join(rollback_parts) + ';' if rollback_parts else ''


def _build_primary_key_where(conn, table: str, row: dict) -> Optional[str]:
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SHOW KEYS FROM {table} WHERE Key_name = 'PRIMARY'")
            pk_rows = cursor.fetchall()
            if pk_rows:
                pk_cols = [pk['Column_name'] for pk in pk_rows]
                where_parts = []
                for col in pk_cols:
                    if col in row:
                        val = row[col]
                        if val is None:
                            where_parts.append(f"{col} IS NULL")
                        elif isinstance(val, (int, float)):
                            where_parts.append(f"{col} = {val}")
                        else:
                            escaped_val = str(val).replace("'", "''")
                            where_parts.append(f"{col} = '{escaped_val}'")
                if where_parts:
                    return ' AND '.join(where_parts)
    except:
        pass
    return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8099)
