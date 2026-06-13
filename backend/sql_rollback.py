import re
from typing import List, Tuple, Optional


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
            if i > 0 and sql[i - 1] == '\\':
                current.append(ch)
                i += 1
                continue
            in_single_quote = not in_single_quote
            current.append(ch)
        elif ch == '"' and not in_single_quote and not in_backtick:
            if i > 0 and sql[i - 1] == '\\':
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


def _get_first_keyword(sql: str) -> str:
    trimmed = sql.strip().lstrip('(').strip()
    if not trimmed:
        return ''
    first_word = re.split(r'\s+', trimmed, maxsplit=1)[0]
    return first_word.upper()


def _extract_table_name(sql: str, keyword: str) -> Optional[str]:
    pattern = rf'\b{keyword}\s+(?:INTO\s+)?FROM\s+([`"\[]?[\w]+[`"\]]?(?:\.[`"\[]?[\w]+[`"\]]?)?)'
    if keyword == 'UPDATE':
        pattern = r'\bUPDATE\s+([`"\[]?[\w]+[`"\]]?(?:\.[`"\[]?[\w]+[`"\]]?)?)'
    elif keyword == 'INSERT':
        pattern = r'\bINSERT\s+(?:INTO\s+)?([`"\[]?[\w]+[`"\]]?(?:\.[`"\[]?[\w]+[`"\]]?)?)'
    elif keyword == 'DELETE':
        pattern = r'\bDELETE\s+FROM\s+([`"\[]?[\w]+[`"\]]?(?:\.[`"\[]?[\w]+[`"\]]?)?)'

    match = re.search(pattern, sql, re.IGNORECASE)
    if match:
        table = match.group(1).strip('`"[]').split('.')[-1]
        return table
    return None


def _extract_where_clause(sql: str) -> Optional[str]:
    match = re.search(r'\bWHERE\s+(.+?)(?:\s+(?:ORDER|GROUP|LIMIT|HAVING|UNION|RETURNING)|;|$)', sql, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _extract_set_clause(sql: str) -> Optional[str]:
    match = re.search(r'\bSET\s+(.+?)(?:\s+WHERE\s|\s+ORDER\s|\s+LIMIT\s|;|$)', sql, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _extract_insert_columns_values(sql: str) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    match = re.search(
        r'INSERT\s+(?:INTO\s+)?[\w`."\[\]]+\s*\((.+?)\)\s*VALUES\s*\((.+?)\)',
        sql,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        cols_str = match.group(1).strip()
        vals_str = match.group(2).strip()
        columns = [c.strip().strip('`"[]') for c in _split_csv(cols_str)]
        values = [v.strip() for v in _split_csv(vals_str)]
        return columns, values
    return None, None


def _split_csv(text: str) -> List[str]:
    items = []
    current = []
    in_quote = False
    in_single_quote = False
    depth = 0

    for ch in text:
        if ch == "'" and not in_quote:
            in_single_quote = not in_single_quote
            current.append(ch)
        elif ch == '"' and not in_single_quote:
            in_quote = not in_quote
            current.append(ch)
        elif ch == '(' and not in_quote and not in_single_quote:
            depth += 1
            current.append(ch)
        elif ch == ')' and not in_quote and not in_single_quote:
            depth -= 1
            current.append(ch)
        elif ch == ',' and not in_quote and not in_single_quote and depth == 0:
            items.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)

    if current:
        items.append(''.join(current).strip())
    return items


def generate_rollback_sql(sql: str) -> Tuple[str, str]:
    sql_clean = _strip_sql_comments(sql)
    statements = _split_statements(sql_clean)

    rollback_statements = []
    query_statements = []

    for stmt in statements:
        first_kw = _get_first_keyword(stmt)

        if first_kw == 'INSERT':
            rb_sql, q_sql = _generate_insert_rollback(stmt)
            rollback_statements.append(rb_sql)
            query_statements.append(q_sql)
        elif first_kw == 'UPDATE':
            rb_sql, q_sql = _generate_update_rollback(stmt)
            rollback_statements.append(rb_sql)
            query_statements.append(q_sql)
        elif first_kw == 'DELETE':
            rb_sql, q_sql = _generate_delete_rollback(stmt)
            rollback_statements.append(rb_sql)
            query_statements.append(q_sql)
        else:
            rollback_statements.append(f'-- 无法生成回滚SQL: {stmt[:100]}...')
            query_statements.append(f'SELECT 1')

    return ';\n'.join(rollback_statements) + ';', ';\n'.join(query_statements) + ';'


def _generate_insert_rollback(stmt: str) -> Tuple[str, str]:
    table = _extract_table_name(stmt, 'INSERT')
    if not table:
        return f'-- 无法解析INSERT语句的表名', 'SELECT 1'

    columns, values = _extract_insert_columns_values(stmt)
    if not columns or not values:
        return f'-- 无法解析INSERT语句的列和值', 'SELECT 1'

    where_conditions = []
    for i, col in enumerate(columns):
        if i < len(values):
            where_conditions.append(f"{col} = {values[i]}")

    where_clause = ' AND '.join(where_conditions)
    rollback_sql = f"DELETE FROM {table} WHERE {where_clause}"
    query_sql = f"SELECT * FROM {table} WHERE {where_clause}"

    return rollback_sql, query_sql


def _generate_update_rollback(stmt: str) -> Tuple[str, str]:
    table = _extract_table_name(stmt, 'UPDATE')
    if not table:
        return f'-- 无法解析UPDATE语句的表名', 'SELECT 1'

    where_clause = _extract_where_clause(stmt)
    if not where_clause:
        return f'-- UPDATE语句缺少WHERE子句，无法生成回滚', 'SELECT 1'

    rollback_sql = f"-- 回滚需要先执行查询获取旧数据: SELECT * FROM {table} WHERE {where_clause}"
    query_sql = f"SELECT * FROM {table} WHERE {where_clause}"

    return rollback_sql, query_sql


def _generate_delete_rollback(stmt: str) -> Tuple[str, str]:
    table = _extract_table_name(stmt, 'DELETE')
    if not table:
        return f'-- 无法解析DELETE语句的表名', 'SELECT 1'

    where_clause = _extract_where_clause(stmt)
    if not where_clause:
        return f'-- DELETE语句缺少WHERE子句，无法生成回滚', 'SELECT 1'

    rollback_sql = f"-- 回滚需要先执行查询获取旧数据: SELECT * FROM {table} WHERE {where_clause}"
    query_sql = f"SELECT * FROM {table} WHERE {where_clause}"

    return rollback_sql, query_sql


def build_update_rollback_from_data(table: str, old_rows: List[dict], where_clause: str) -> str:
    if not old_rows:
        return '-- 没有旧数据，无需回滚'

    statements = []
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
        statements.append(f"UPDATE {table} SET {set_clause} WHERE {where_clause} LIMIT 1")

    return ';\n'.join(statements) + ';'


def build_delete_rollback_from_data(table: str, old_rows: List[dict]) -> str:
    if not old_rows:
        return '-- 没有旧数据，无需回滚'

    statements = []
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
        statements.append(f"INSERT INTO {table} ({cols_str}) VALUES ({vals_str})")

    return ';\n'.join(statements) + ';'


def is_write_operation(sql: str) -> bool:
    sql_clean = _strip_sql_comments(sql)
    statements = _split_statements(sql_clean)

    for stmt in statements:
        first_kw = _get_first_keyword(stmt)
        if first_kw in ('INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'REPLACE'):
            return True

    return False
