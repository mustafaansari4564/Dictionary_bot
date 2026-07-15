import sqlite3
from text_utils import normalize


def _normalize_row(row: dict) -> dict:
    """
    Guarantee the rest of the code always sees the same 5 keys,
    regardless of what column names a particular .db file uses.

    Handles two known layouts:
      • Standard (built by convert_lane.py):  root, root_normalized, page_num, title, entry_text
      • Qamus / custom builds:                root, root_normalized, entry_text  (no page_num / title)
    """
    return {
        'root':            row.get('root')            or row.get('key')      or '',
        'root_normalized': row.get('root_normalized') or row.get('root')     or '',
        'page_num':        row.get('page_num')        or row.get('page')     or None,
        'title':           row.get('title')           or row.get('headword') or row.get('head') or '',
        'entry_text':      row.get('entry_text')      or row.get('text')     or row.get('xml')  or '',
    }


def _get_columns(conn, table: str) -> set[str]:
    """Return the set of column names for a table."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def lookup_root(db_path: str, root: str) -> list[dict]:
    """Exact root lookup — primary path. Works with any entries schema."""
    norm = normalize(root)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Check if page_num exists so we can ORDER BY it safely
    cols = _get_columns(conn, 'entries')
    order = 'ORDER BY page_num' if 'page_num' in cols else ''

    try:
        rows = conn.execute(f"""
            SELECT *
            FROM   entries
            WHERE  root_normalized = ?
            {order}
            LIMIT  3
        """, (norm,)).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [_normalize_row(dict(r)) for r in rows]


def fuzzy_lookup(db_path: str, root: str) -> list[dict]:
    """FTS5 full-text fallback when exact match returns nothing."""
    norm = normalize(root)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT e.*
            FROM   entries_fts f
            JOIN   entries e ON e.id = f.rowid
            WHERE  entries_fts MATCH ?
            ORDER  BY rank
            LIMIT  3
        """, (f'"{norm}"',)).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [_normalize_row(dict(r)) for r in rows]


def search_nearby_roots(db_path: str, root: str) -> list[str]:
    """Suggest roots sharing the first 2 letters when exact match fails."""
    norm = normalize(root)
    if len(norm) < 2:
        return []
    prefix = norm[:2]
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("""
            SELECT DISTINCT root
            FROM   entries
            WHERE  root_normalized LIKE ?
            LIMIT  6
        """, (f'{prefix}%',)).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [r[0] for r in rows]