from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    image_file_id TEXT,
    video_file_id TEXT,
    audio_file_id TEXT,
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id);
"""


@dataclass(slots=True)
class HistoryItem:
    id: int
    user_id: int
    kind: str
    title: str
    image_file_id: str | None
    video_file_id: str | None
    audio_file_id: str | None
    meta: dict[str, Any]
    created_at: str


class HistoryStore:
    def __init__(self, db_path: Path, max_per_user: int = 30) -> None:
        self._db_path = db_path
        self._max_per_user = max_per_user
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def add(
        self,
        user_id: int,
        kind: str,
        title: str,
        *,
        image_file_id: str | None = None,
        video_file_id: str | None = None,
        audio_file_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> HistoryItem:
        assert self._conn
        await self._trim_old(user_id)
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(meta or {}, ensure_ascii=False)
        cursor = await self._conn.execute(
            """
            INSERT INTO history (
                user_id, kind, title, image_file_id, video_file_id,
                audio_file_id, meta_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                kind,
                title[:80],
                image_file_id,
                video_file_id,
                audio_file_id,
                payload,
                now,
            ),
        )
        await self._conn.commit()
        return HistoryItem(
            id=int(cursor.lastrowid),
            user_id=user_id,
            kind=kind,
            title=title[:80],
            image_file_id=image_file_id,
            video_file_id=video_file_id,
            audio_file_id=audio_file_id,
            meta=meta or {},
            created_at=now,
        )

    async def get(self, user_id: int, item_id: int) -> HistoryItem | None:
        assert self._conn
        cursor = await self._conn.execute(
            """
            SELECT id, user_id, kind, title, image_file_id, video_file_id,
                   audio_file_id, meta_json, created_at
            FROM history WHERE user_id = ? AND id = ?
            """,
            (user_id, item_id),
        )
        row = await cursor.fetchone()
        return self._row_to_item(row) if row else None

    async def list_for_user(self, user_id: int, *, limit: int = 15) -> list[HistoryItem]:
        assert self._conn
        cursor = await self._conn.execute(
            """
            SELECT id, user_id, kind, title, image_file_id, video_file_id,
                   audio_file_id, meta_json, created_at
            FROM history WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    async def _trim_old(self, user_id: int) -> None:
        assert self._conn
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM history WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        count = int(row[0])
        if count < self._max_per_user:
            return
        to_delete = count - self._max_per_user + 1
        await self._conn.execute(
            """
            DELETE FROM history WHERE id IN (
                SELECT id FROM history WHERE user_id = ?
                ORDER BY id ASC LIMIT ?
            )
            """,
            (user_id, to_delete),
        )

    @staticmethod
    def _row_to_item(row: aiosqlite.Row) -> HistoryItem:
        return HistoryItem(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            kind=str(row["kind"]),
            title=str(row["title"]),
            image_file_id=row["image_file_id"],
            video_file_id=row["video_file_id"],
            audio_file_id=row["audio_file_id"],
            meta=json.loads(row["meta_json"] or "{}"),
            created_at=str(row["created_at"]),
        )
