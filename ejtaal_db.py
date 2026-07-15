"""
ejtaal_db.py — Query functions for ejtaal_index.db
"""
import sqlite3
import os
from text_utils import normalize


# ── Image URL builder ─────────────────────────────────────────────────────────

def build_image_url(img_prefix: str, page_num: int, image_base: str) -> str:
    """
    Construct the ejtaal.net image URL for a given dict and page.

    New format (confirmed Jun 2026):
        {base}/{img_prefix}/{page_num // 100}/{img_prefix}-{page_num:04d}.png

    Examples:
        ll,  2581 → .../ll/25/ll-2581.png
        umj,  640 → .../umj/6/umj-0640.png
        la,  3527 → .../la/35/la-3527.png
        hw4,  883 → .../hw4/8/hw4-0883.png
    """
    folder = page_num // 100
    return f"{image_base}/{img_prefix}/{folder}/{img_prefix}-{page_num:04d}.png"


# ── Page search ───────────────────────────────────────────────────────────────

def find_page(conn: sqlite3.Connection, dict_code: str, root: str):
    """
    Find which image page a root appears on.

    Uses a lower-bound search: MIN(page_num) WHERE page_root_n >= root.
    This matches ejtaal.net's own JS binary search exactly:
      - Exact match  → first page of that root (not the last)
      - Between roots → first page of the next root (not the previous)

    Fallback: if root sorts after every entry, return the last page.
    """
    norm = normalize(root)

    row = conn.execute(
        """
        SELECT MIN(page_num)
        FROM   dict_pages
        WHERE  dict_code   = ?
          AND  page_root_n >= ?
        """,
        (dict_code, norm)
    ).fetchone()

    if row and row[0] is not None:
        return row[0]

    # Root sorts after everything in this dict — return the last page
    row2 = conn.execute(
        "SELECT MAX(page_num) FROM dict_pages WHERE dict_code = ?",
        (dict_code,)
    ).fetchone()

    return row2[0] if row2 else None


# ── Multi-dict search ─────────────────────────────────────────────────────────

def search_all(db_path: str, root: str, lang_filter: str = None) -> list:
    """
    Search for root across all (or filtered) dictionaries.

    Returns a list of result dicts, each containing:
        code, name, lang, img_prefix, color, page_num
    """
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = "SELECT code, name, lang, img_prefix, offset, color FROM dicts"
    params = []
    if lang_filter and lang_filter != 'all':
        query += " WHERE lang = ?"
        params.append(lang_filter)
    query += " ORDER BY lang, name"

    dicts = conn.execute(query, params).fetchall()

    results = []
    for d in dicts:
        page = find_page(conn, d['code'], root)
        if page is not None:
            results.append({
                'code':       d['code'],
                'name':       d['name'],
                'lang':       d['lang'],
                'img_prefix': d['img_prefix'],
                'color':      d['color'],
                'page_num':   page,
            })

    conn.close()
    return results


# ── Available dicts ───────────────────────────────────────────────────────────

def get_available_dicts(db_path: str) -> list:
    """Return metadata for all indexed dictionaries."""
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT code, name, lang, img_prefix, color FROM dicts ORDER BY lang, name"
    ).fetchall()

    conn.close()
    return [dict(r) for r in rows]