import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RiskCheckResult:
    blocked: bool = False
    reasons: List[str] = field(default_factory=list)
    severity: str = "low"
    risk_type: str = ""

    @property
    def is_risky(self) -> bool:
        return self.blocked or len(self.reasons) > 0


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    return sql


def _split_statements(sql: str) -> List[str]:
    statements = []
    current = []
    in_single_quote = False
    in_double_quote = False
    in_backtick = False

    i = 0
    while i < len(sql):
        ch = sql[i]

        if ch == "'" and not in_double_quote and not in_backtick:
            if i > 0 and sql[i-1] == '\\':
                current.append(ch)
                i += 1
                continue
            in_single_quote = not in_single_quote
            current.append(ch)
        elif ch == '"' and not in_single_quote and not in_backtick:
            if i > 0 and sql[i-1] == '\\':
                current.append(ch)
                i += 1
                continue
            in_double_quote = not in_double_quote
            current.append(ch)
        elif ch == '`' and not in_single_quote and not in_double_quote:
            in_backtick = not in_backtick
            current.append(ch)
        elif ch == ';' and not in_single_quote and not in_double_quote and not in_backtick:
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(ch)
        i += 1

    last = ''.join(current).strip()
    if last:
        statements.append(last)

    return statements


def _extract_tables(sql: str) -> List[str]:
    tables = set()
    patterns = [
        r'\b(?:FROM|JOIN|UPDATE|INTO|TABLE)\s+([`"\[]?[\w]+[`"\]]?(?:\.[`"\[]?[\w]+[`"\]]?)?)',
        r'\bTRUNCATE\s+(?:TABLE\s+)?([`"\[]?[\w]+[`"\]]?(?:\.[`"\[]?[\w]+[`"\]]?)?)',
        r'\bDROP\s+(?:TABLE|VIEW|DATABASE|SCHEMA)\s+(?:IF\s+EXISTS\s+)?([`"\[]?[\w]+[`"\]]?(?:\.[`"\[]?[\w]+[`"\]]?)?)',
        r'\bDELETE\s+FROM\s+([`"\[]?[\w]+[`"\]]?(?:\.[`"\[]?[\w]+[`"\]]?)?)',
    ]
    for p in patterns:
        for m in re.finditer(p, sql, re.IGNORECASE):
            tbl = m.group(1).strip('`"[]').split('.')[-1]
            tables.add(tbl.lower())
    return list(tables)


def _get_first_keyword(sql: str) -> str:
    trimmed = sql.strip().lstrip('(').strip()
    if not trimmed:
        return ''
    first_word = re.split(r'\s+', trimmed, maxsplit=1)[0]
    return first_word.upper()


def _has_trivial_where(sql: str) -> bool:
    match = re.search(r'\bWHERE\s+(.+?)(?:\s+(?:ORDER|GROUP|LIMIT|HAVING|UNION)|;|$)', sql, re.IGNORECASE | re.DOTALL)
    if not match:
        return False
    where_clause = match.group(1).strip()
    trivial_patterns = [
        r'^\s*1\s*=\s*1\s*$',
        r'^\s*TRUE\s*$',
        r'^\s*\'.*\'\s*=\s*\'.*\'\s*$',
        r'^\s*0\s*=\s*0\s*$',
    ]
    for pat in trivial_patterns:
        if re.match(pat, where_clause, re.IGNORECASE):
            return True
    return False


def check_update_without_where(sql: str) -> Optional[str]:
    first_kw = _get_first_keyword(sql)
    if first_kw != 'UPDATE':
        return None
    if not re.search(r'\bWHERE\b', sql, re.IGNORECASE):
        return 'UPDATE 语句缺少 WHERE 子句，属于高危全表更新操作'
    if _has_trivial_where(sql):
        return 'UPDATE 语句 WHERE 条件恒真，属于高危全表更新操作'
    return None


def check_delete_without_where(sql: str) -> Optional[str]:
    first_kw = _get_first_keyword(sql)
    if first_kw != 'DELETE' and not re.match(r'^DELETE\s+FROM', sql, re.IGNORECASE):
        return None
    if not re.search(r'\bWHERE\b', sql, re.IGNORECASE):
        return 'DELETE 语句缺少 WHERE 子句，属于高危全表删除操作'
    if _has_trivial_where(sql):
        return 'DELETE 语句 WHERE 条件恒真，属于高危全表删除操作'
    return None


def check_drop_operation(sql: str) -> Optional[str]:
    match = re.search(r'\bDROP\s+(TABLE|VIEW|DATABASE|SCHEMA|INDEX|PROCEDURE|FUNCTION|TRIGGER)\b', sql, re.IGNORECASE)
    if match:
        op = match.group(1).upper()
        return f'检测到 DROP {op} 操作，属于高危破坏性操作'
    return None


def check_truncate_operation(sql: str) -> Optional[str]:
    if re.search(r'\bTRUNCATE\b', sql, re.IGNORECASE):
        return '检测到 TRUNCATE 操作，属于高危全表清空操作'
    return None


def check_alter_operation(sql: str) -> Optional[str]:
    match = re.search(r'\bALTER\s+(TABLE|DATABASE|SCHEMA|VIEW|PROCEDURE|FUNCTION)\b', sql, re.IGNORECASE)
    if match:
        op = match.group(1).upper()
        return f'检测到 ALTER {op} 结构变更操作'
    return None


def check_create_dangerous(sql: str) -> Optional[str]:
    match = re.search(r'\bCREATE\s+(TABLE|DATABASE|VIEW)\s+AS\b', sql, re.IGNORECASE)
    if match:
        op = match.group(1).upper()
        return f'检测到 CREATE {op} AS 批量建表操作'
    return None


def check_insert_select(sql: str) -> Optional[str]:
    if re.search(r'\bINSERT\s+(?:INTO\s+)?[\w`."\[\]]+\s+SELECT\b', sql, re.IGNORECASE | re.DOTALL):
        return '检测到 INSERT ... SELECT 批量插入操作'
    return None


def check_replace_operation(sql: str) -> Optional[str]:
    first_kw = _get_first_keyword(sql)
    if first_kw == 'REPLACE':
        return '检测到 REPLACE 操作，属于高危覆盖更新操作'
    return None


def check_multi_statement(sql: str) -> Optional[str]:
    stmts = _split_statements(sql)
    if len(stmts) > 1:
        return f'检测到多条 SQL 语句（共 {len(stmts)} 条），存在注入风险'
    return None


def check_dangerous_functions(sql: str) -> Optional[str]:
    dangerous_funcs = [
        (r'\bSLEEP\s*\(', 'SLEEP 休眠函数'),
        (r'\bBENCHMARK\s*\(', 'BENCHMARK 性能测试函数'),
        (r'\bLOAD_FILE\s*\(', 'LOAD_FILE 文件读取函数'),
        (r'\bINTO\s+OUTFILE\b', 'INTO OUTFILE 文件导出'),
        (r'\bINTO\s+DUMPFILE\b', 'INTO DUMPFILE 文件导出'),
        (r'\bGROUP_CONCAT\s*\(', 'GROUP_CONCAT 聚合函数'),
    ]
    for pattern, name in dangerous_funcs:
        if re.search(pattern, sql, re.IGNORECASE):
            return f'检测到危险函数 {name}，存在安全风险'
    return None


def check_sensitive_tables(sql: str, regex_rules: List) -> List[str]:
    tables = _extract_tables(sql)
    reasons = []
    for rule in regex_rules:
        try:
            pattern = re.compile(rule.pattern, re.IGNORECASE)
            for tbl in tables:
                if pattern.search(tbl):
                    reasons.append(f"访问敏感表 '{tbl}'，命中规则 [{rule.name}]：{rule.description or rule.pattern}")
        except re.error:
            continue
    return reasons


def run_risk_check(sql: str, regex_rules: List = None) -> RiskCheckResult:
    sql_clean = _strip_sql_comments(sql)
    reasons = []
    blocked = False
    severity = "low"

    multi_stmt_reason = check_multi_statement(sql_clean)
    if multi_stmt_reason:
        reasons.append(multi_stmt_reason)
        blocked = True
        severity = "high"

    statements = _split_statements(sql_clean)

    blocking_checks = [
        (check_update_without_where, "high"),
        (check_delete_without_where, "high"),
        (check_drop_operation, "high"),
        (check_truncate_operation, "high"),
        (check_replace_operation, "high"),
        (check_dangerous_functions, "high"),
    ]

    warning_checks = [
        (check_alter_operation, "medium"),
        (check_create_dangerous, "medium"),
        (check_insert_select, "medium"),
    ]

    for stmt in statements:
        for check_fn, sev in blocking_checks:
            reason = check_fn(stmt)
            if reason:
                reasons.append(reason)
                blocked = True
                if sev == "high":
                    severity = "high"
                elif sev == "medium" and severity != "high":
                    severity = "medium"

        for check_fn, sev in warning_checks:
            reason = check_fn(stmt)
            if reason:
                reasons.append(reason)
                if sev == "high":
                    severity = "high"
                elif sev == "medium" and severity != "high":
                    severity = "medium"

    if regex_rules:
        sensitive_reasons = check_sensitive_tables(sql_clean, regex_rules)
        for sr in sensitive_reasons:
            reasons.append(sr)
            blocked = True
            severity = "high"

    return RiskCheckResult(
        blocked=blocked,
        reasons=reasons,
        severity=severity,
        risk_type="high_risk_operation" if blocked else ("warning" if reasons else "normal")
    )
