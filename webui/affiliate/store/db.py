"""
SQLite database for the Shopee Affiliate Pipeline.

Tables:
  fb_pages   — Facebook Pages đã kết nối
  products   — Sản phẩm Shopee (1 link = 1 row)
  campaigns  — Mỗi kịch bản/video = 1 row, liên kết tới product
  settings   — Key-value store cho cài đặt ứng dụng
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent / "storage" / "affiliate.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS fb_pages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    page_id     TEXT NOT NULL UNIQUE,
    token       TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    shopee_url   TEXT NOT NULL,
    name         TEXT DEFAULT '',
    price        TEXT DEFAULT '',
    image_url    TEXT DEFAULT '',
    insights     TEXT DEFAULT '',   -- JSON: {target, pain_points, hooks}
    page_id      INTEGER REFERENCES fb_pages(id),
    script_count INTEGER DEFAULT 3,
    status       TEXT DEFAULT 'pending',
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS campaigns (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    hook_type    TEXT DEFAULT '',   -- 'curiosity' | 'shock' | 'benefit'
    hook_text    TEXT DEFAULT '',
    script       TEXT DEFAULT '',
    video_terms  TEXT DEFAULT '',   -- JSON list
    task_id      TEXT DEFAULT '',   -- MoneyPrinterTurbo task ID
    caption      TEXT DEFAULT '',   -- Caption đăng bài (hook + link + hashtag)
    video_path   TEXT DEFAULT '',
    status       TEXT DEFAULT 'draft',
    -- draft | scripting | rendering | scheduled | posted | error
    scheduled_at TEXT DEFAULT '',
    posted_at    TEXT DEFAULT '',
    post_id      TEXT DEFAULT '',   -- Facebook post ID sau khi đăng
    views        INTEGER DEFAULT 0,
    likes        INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript(SCHEMA)
        _migrate(con)


def _migrate(con):
    """Thêm cột mới cho DB cũ (idempotent)."""
    existing = {r["name"] for r in con.execute("PRAGMA table_info(campaigns)").fetchall()}
    if "caption" not in existing:
        con.execute("ALTER TABLE campaigns ADD COLUMN caption TEXT DEFAULT ''")


# ── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    with _conn() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    with _conn() as con:
        con.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_all_settings() -> dict:
    with _conn() as con:
        rows = con.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


# ── Facebook Pages ─────────────────────────────────────────────────────────────

def list_pages() -> list[dict]:
    with _conn() as con:
        rows = con.execute("SELECT * FROM fb_pages ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def add_page(name: str, page_id: str, token: str) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT OR REPLACE INTO fb_pages(name,page_id,token) VALUES(?,?,?)",
            (name, page_id, token),
        )
    return cur.lastrowid


def delete_page(page_id: str):
    with _conn() as con:
        con.execute("DELETE FROM fb_pages WHERE page_id=?", (page_id,))


# ── Products ───────────────────────────────────────────────────────────────────

def list_products(status_filter: str = "") -> list[dict]:
    sql = "SELECT p.*, f.name as page_name FROM products p LEFT JOIN fb_pages f ON p.page_id=f.id"
    params: tuple = ()
    if status_filter:
        sql += " WHERE p.status=?"
        params = (status_filter,)
    sql += " ORDER BY p.created_at DESC"
    with _conn() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_product(product_id: int) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT p.*, f.name as page_name FROM products p "
            "LEFT JOIN fb_pages f ON p.page_id=f.id WHERE p.id=?",
            (product_id,),
        ).fetchone()
    return dict(row) if row else None


def add_product(shopee_url: str, page_id: int | None, script_count: int = 3) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO products(shopee_url, page_id, script_count, status) VALUES(?,?,?,'analyzing')",
            (shopee_url, page_id, script_count),
        )
    return cur.lastrowid


def update_product(product_id: int, **fields):
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with _conn() as con:
        con.execute(
            f"UPDATE products SET {set_clause} WHERE id=?",
            (*fields.values(), product_id),
        )


def delete_product(product_id: int):
    with _conn() as con:
        con.execute("DELETE FROM products WHERE id=?", (product_id,))


# ── Campaigns ──────────────────────────────────────────────────────────────────

def list_campaigns(product_id: int) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM campaigns WHERE product_id=? ORDER BY id",
            (product_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_all_campaigns() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT c.*, p.name as product_name, p.shopee_url, f.name as page_name "
            "FROM campaigns c "
            "JOIN products p ON c.product_id=p.id "
            "LEFT JOIN fb_pages f ON p.page_id=f.id "
            "ORDER BY c.created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def add_campaign(product_id: int, hook_type: str, hook_text: str, script: str) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO campaigns(product_id,hook_type,hook_text,script,status) VALUES(?,?,?,?,'draft')",
            (product_id, hook_type, hook_text, script),
        )
    return cur.lastrowid


def update_campaign(campaign_id: int, **fields):
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with _conn() as con:
        con.execute(
            f"UPDATE campaigns SET {set_clause} WHERE id=?",
            (*fields.values(), campaign_id),
        )


def delete_campaign(campaign_id: int):
    with _conn() as con:
        con.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))


# ── Dashboard stats ────────────────────────────────────────────────────────────

def get_stats() -> dict:
    with _conn() as con:
        total_posted = con.execute(
            "SELECT COUNT(*) as n FROM campaigns WHERE status='posted'"
        ).fetchone()["n"]
        total_views = con.execute(
            "SELECT COALESCE(SUM(views),0) as n FROM campaigns"
        ).fetchone()["n"]
        total_likes = con.execute(
            "SELECT COALESCE(SUM(likes),0) as n FROM campaigns"
        ).fetchone()["n"]
        pending_post = con.execute(
            "SELECT COUNT(*) as n FROM campaigns WHERE status IN ('scheduled','draft','rendering')"
        ).fetchone()["n"]
        posted_dates = con.execute(
            "SELECT DATE(posted_at) as d, COUNT(*) as n FROM campaigns "
            "WHERE status='posted' AND posted_at!='' "
            "GROUP BY DATE(posted_at)"
        ).fetchall()
        scheduled_dates = con.execute(
            "SELECT DATE(scheduled_at) as d, COUNT(*) as n FROM campaigns "
            "WHERE status='scheduled' AND scheduled_at!='' "
            "GROUP BY DATE(scheduled_at)"
        ).fetchall()
    return {
        "total_posted": total_posted,
        "total_views": total_views,
        "total_likes": total_likes,
        "pending_post": pending_post,
        "posted_dates": {r["d"]: r["n"] for r in posted_dates},
        "scheduled_dates": {r["d"]: r["n"] for r in scheduled_dates},
    }


def get_top_campaigns(limit: int = 5) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT c.*, p.name as product_name FROM campaigns c "
            "JOIN products p ON c.product_id=p.id "
            "WHERE c.status='posted' "
            "ORDER BY c.views DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_campaigns_for_date(date_str: str) -> list[dict]:
    """date_str: 'YYYY-MM-DD'"""
    with _conn() as con:
        rows = con.execute(
            "SELECT c.*, p.name as product_name FROM campaigns c "
            "JOIN products p ON c.product_id=p.id "
            "WHERE DATE(c.scheduled_at)=? OR DATE(c.posted_at)=?",
            (date_str, date_str),
        ).fetchall()
    return [dict(r) for r in rows]
