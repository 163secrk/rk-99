import re
from typing import List, Any


PRESET_MASK_TYPES = {
    "phone": {"keep_prefix": 3, "keep_suffix": 4, "mask_char": "*"},
    "id_card": {"keep_prefix": 3, "keep_suffix": 4, "mask_char": "*"},
    "salary": {"keep_prefix": 0, "keep_suffix": 2, "mask_char": "*"},
    "name": {"keep_prefix": 1, "keep_suffix": 0, "mask_char": "*"},
}


def mask_value(value: Any, mask_type: str, keep_prefix: int = 0, keep_suffix: int = 0, mask_char: str = "*") -> Any:
    if value is None:
        return None

    text = str(value)
    if len(text) == 0:
        return text

    preset = PRESET_MASK_TYPES.get(mask_type)
    if preset:
        keep_prefix = preset["keep_prefix"]
        keep_suffix = preset["keep_suffix"]
        mask_char = preset["mask_char"]

    total_len = len(text)
    prefix_part = text[:keep_prefix] if keep_prefix > 0 else ""
    suffix_part = text[total_len - keep_suffix:] if keep_suffix > 0 else ""
    middle_len = total_len - keep_prefix - keep_suffix

    if middle_len <= 0:
        return text

    masked_middle = mask_char * middle_len
    return prefix_part + masked_middle + suffix_part


def match_columns(columns: List[str], column_pattern: str) -> List[int]:
    matched_indices = []
    try:
        pattern = re.compile(column_pattern, re.IGNORECASE)
    except re.error:
        lower_pattern = column_pattern.lower()
        for i, col in enumerate(columns):
            if col.lower() == lower_pattern:
                matched_indices.append(i)
        return matched_indices

    for i, col in enumerate(columns):
        if pattern.search(col):
            matched_indices.append(i)
    return matched_indices


def apply_masking(columns: List[str], rows: List[List[Any]], masking_rules: List) -> tuple:
    if not masking_rules or not columns or not rows:
        return columns, rows

    active_rules = [r for r in masking_rules if r.is_active]
    if not active_rules:
        return columns, rows

    masked_columns = list(columns)
    masked_rows = [list(row) for row in rows]

    masked_flags = [False] * len(columns)

    for rule in active_rules:
        matched_indices = match_columns(columns, rule.column_pattern)
        for idx in matched_indices:
            masked_flags[idx] = True
            for row in masked_rows:
                row[idx] = mask_value(
                    row[idx],
                    mask_type=rule.mask_type,
                    keep_prefix=rule.keep_prefix,
                    keep_suffix=rule.keep_suffix,
                    mask_char=rule.mask_char or "*"
                )

    for i, flag in enumerate(masked_flags):
        if flag:
            masked_columns[i] = f"{columns[i]}🔒"

    return masked_columns, masked_rows
