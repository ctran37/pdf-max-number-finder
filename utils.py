from collections.abc import Iterator
from dataclasses import dataclass

from config import (
    NUMBER_PATTERN,
    SCALE_PHRASE_PATTERNS,
    LOCAL_SCALE_PATTERNS,
    SCALE_NAMES,
    NON_FINANCIAL_PATTERN,
)


# Data types
@dataclass
class Hit:
    raw: float
    scaled: float
    num_str: str
    scale_source: str
    page: int
    location: str  # e.g. "line 14" or "table 1, row 3"
    context: str   # surrounding text or cell content


@dataclass
class ScaleResult:
    multiplier: float
    label: str


# Processing
def process_table(table: list, page_num: int, t_idx: int, page_scale: int | None = None) -> tuple[Hit | None, Hit | None]:
    table_scale = detect_table_scale(table)
    effective_scale = table_scale or page_scale

    best_raw = best_scaled = None

    for row_idx, row in enumerate(table):
        if not row:
            continue
        row_label = (row[0] or "").strip()
        # suppress scale for headcount/personnel rows to avoid false positives
        row_scale = None if NON_FINANCIAL_PATTERN.search(row_label) else effective_scale
        for col_idx, cell in enumerate(row):
            if not cell or not cell.strip():
                continue
            cell = cell.strip()
            for num_str, idx in extract_numbers_with_positions(cell):
                raw = clean_number(num_str)
                result = resolve_scale(num_str, raw, cell, idx + len(num_str), row_scale)
                if result.label == "none (year)":
                    continue
                scaled = raw * result.multiplier
                location = f"table {t_idx + 1}, row {row_idx}"
                hit = Hit(raw, scaled, num_str, result.label, page_num, location, cell)
                best_raw = better_raw(best_raw, hit)
                best_scaled = better_scaled(best_scaled, hit)

    return best_raw, best_scaled


def process_chunk(
    chunk: str, chunk_start: int, page_text: str, page_num: int, effective_scale: int | None = None
) -> tuple[Hit | None, Hit | None]:
    best_raw = best_scaled = None

    for num_str, idx in extract_numbers_with_positions(chunk):
        raw = clean_number(num_str)
        abs_pos = chunk_start + idx
        result = resolve_scale(
            num_str, raw, chunk, idx + len(num_str), effective_scale,
            page_text=page_text, abs_pos=abs_pos,
        )
        if result.label == "none (year)":
            continue
        scaled = raw * result.multiplier
        line_num, context = line_and_context(page_text, abs_pos)
        hit = Hit(raw, scaled, num_str, result.label, page_num, f"line {line_num}", context)
        best_raw = better_raw(best_raw, hit)
        best_scaled = better_scaled(best_scaled, hit)

    return best_raw, best_scaled


# Hit comparison
def better_raw(a: Hit | None, b: Hit | None) -> Hit | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if a.raw >= b.raw else b


def better_scaled(a: Hit | None, b: Hit | None) -> Hit | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if a.scaled >= b.scaled else b


# Scale resolution
def resolve_scale(
    num_str: str,
    raw: float,
    text: str,
    num_end: int,
    effective_scale: int | None,
    page_text: str | None = None,
    abs_pos: int | None = None,
) -> ScaleResult:
    """
    Returns a ScaleResult with the multiplier and label to apply to a number.
    Pass page_text + abs_pos to enable the isolated-number check (prose only).
    """
    if is_year(raw):
        return ScaleResult(1, "none (year)")
    if page_text is not None and abs_pos is not None and is_isolated_number(page_text, abs_pos, num_str):
        return ScaleResult(1, "none (isolated)")
    local_mult, local_name = find_local_scale(text, num_end)
    if local_mult:
        return ScaleResult(local_mult, f"local ({local_name})")
    if effective_scale and not already_at_full_scale(num_str, raw, effective_scale):
        return ScaleResult(effective_scale, SCALE_NAMES[effective_scale])
    return ScaleResult(1, "none (already full scale)" if effective_scale else "none")


# Scale detection
def detect_scale(text: str) -> int | None:
    for pattern, multiplier in SCALE_PHRASE_PATTERNS:
        if pattern.search(text):
            return multiplier
    return None


def detect_table_scale(table: list) -> int | None:
    for row in table[:3]:
        for cell in (row or []):
            if cell:
                scale = detect_scale(cell)
                if scale:
                    return scale
    return None


def find_local_scale(text: str, num_end: int, window: int = 40) -> tuple[int | None, str | None]:
    snippet = text[num_end: num_end + window]
    for pattern, multiplier in LOCAL_SCALE_PATTERNS:
        if pattern.search(snippet):
            return multiplier, SCALE_NAMES[multiplier]
    return None, None


# Number classification
def is_year(raw: float) -> bool:
    return raw == int(raw) and 1900 <= raw <= 2099


def is_isolated_number(page_text: str, abs_pos: int, num_str: str) -> bool:
    line_start = page_text.rfind('\n', 0, abs_pos) + 1
    line_end = page_text.find('\n', abs_pos)
    if line_end == -1:
        line_end = len(page_text)
    remainder = page_text[line_start:line_end].replace(num_str, '').replace('$', '').strip()
    return len(remainder) == 0


def already_at_full_scale(num_str: str, raw: float, scale: int) -> bool:
    if '$' in num_str:
        return True
    if ',' in num_str and raw >= scale:
        return True
    # Count only digits in the integer part so "5,279.055" (4 integer digits) isn't
    # confused with "5192166" (7 integer digits).
    integer_digits = sum(c.isdigit() for c in num_str.split('.')[0])
    if integer_digits >= 7:
        return True
    return False


# Number parsing
def extract_numbers_with_positions(text: str) -> list[tuple[str, int]]:
    return [(m.group(), m.start()) for m in NUMBER_PATTERN.finditer(text)]


def clean_number(num_str: str) -> float:
    return float(num_str.replace(",", "").replace("$", ""))


# PDF page utilities
def get_prose_text(page, table_bboxes: list[tuple]) -> str:
    if not table_bboxes:
        return page.extract_text() or ""
    return page.filter(lambda obj: not _in_any_table(obj, table_bboxes)).extract_text() or ""


def _in_any_table(obj, table_bboxes: list[tuple]) -> bool:
    for x0, top, x1, bottom in table_bboxes:
        if (x0 <= obj.get('x0', 0) and obj.get('x1', 0) <= x1
                and top <= obj.get('top', 0) and obj.get('bottom', 0) <= bottom):
            return True
    return False


# Text utilities
def chunk_text(text: str, size: int = 1000, overlap: int = 100) -> Iterator[tuple[str, int]]:
    # overlap prevents scale keywords near a chunk boundary from being missed
    start = 0
    while start < len(text):
        yield text[start: start + size], start
        start += size - overlap


def line_and_context(page_text: str, abs_pos: int, window: int = 60) -> tuple[int, str]:
    line_num = page_text[:abs_pos].count('\n') + 1
    snippet_start = max(0, abs_pos - window)
    snippet_end = min(len(page_text), abs_pos + window)
    context = page_text[snippet_start:snippet_end].replace('\n', ' ').strip()
    return line_num, context
