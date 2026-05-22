"""
database.py — all DB operations (async SQLite via aiosqlite)
"""

import aiosqlite
from config import DB_PATH


# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS examples (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    text        TEXT    NOT NULL,
    image_url   TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pending_posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    text        TEXT    NOT NULL,
    image_url   TEXT,
    status      TEXT    DEFAULT 'pending',   -- pending | approved | rejected
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()


# ── Examples ──────────────────────────────────────────────────────────────────

async def add_example(text: str, image_url: str | None = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO examples (text, image_url) VALUES (?, ?)",
            (text, image_url),
        )
        await db.commit()
        return cursor.lastrowid


async def get_examples(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM examples ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def delete_example(example_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM examples WHERE id = ?", (example_id,))
        await db.commit()


# ── Pending posts ─────────────────────────────────────────────────────────────

async def add_pending_post(text: str, image_url: str | None = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO pending_posts (text, image_url) VALUES (?, ?)",
            (text, image_url),
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_post(post_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM pending_posts WHERE id = ?", (post_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_post_status(post_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pending_posts SET status = ? WHERE id = ?", (status, post_id)
        )
        await db.commit()


async def get_all_pending() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM pending_posts WHERE status = 'pending' ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
