from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from bot.models.avatar_config import AvatarConfig

log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    avatar_file_id TEXT NOT NULL,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
"""


@dataclass(slots=True)
class Favorite:
    id: int
    user_id: int
    name: str
    avatar_file_id: str
    config: AvatarConfig
    created_at: str


class FavoritesStore:
    def __init__(self, db_path: Path, max_per_user: int) -> None:
        self._db_path = db_path
        self._max_per_user = max_per_user
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()
        log.info("Favorites DB ready at %s", self._db_path)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def count(self, user_id: int) -> int:
        assert self._conn
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM favorites WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return int(row[0])

    async def list_for_user(self, user_id: int, *, limit: int = 20) -> list[Favorite]:
        assert self._conn
        cursor = await self._conn.execute(
            """
            SELECT id, user_id, name, avatar_file_id, config_json, created_at
            FROM favorites
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_favorite(row) for row in rows]

    async def get(self, user_id: int, favorite_id: int) -> Favorite | None:
        assert self._conn
        cursor = await self._conn.execute(
            """
            SELECT id, user_id, name, avatar_file_id, config_json, created_at
            FROM favorites
            WHERE user_id = ? AND id = ?
            """,
            (user_id, favorite_id),
        )
        row = await cursor.fetchone()
        return self._row_to_favorite(row) if row else None

    async def add(
        self,
        user_id: int,
        name: str,
        avatar_file_id: str,
        config: AvatarConfig,
    ) -> Favorite | None:
        assert self._conn
        count = await self.count(user_id)
        if count >= self._max_per_user:
            return None

        clean_name = name.strip()[:64] or config.auto_name()
        now = datetime.now(timezone.utc).isoformat()
        config_payload = json.dumps(config.to_dict(), ensure_ascii=False)
        cursor = await self._conn.execute(
            """
            INSERT INTO favorites (user_id, name, avatar_file_id, config_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, clean_name, avatar_file_id, config_payload, now),
        )
        await self._conn.commit()
        fav_id = cursor.lastrowid
        return Favorite(
            id=int(fav_id),
            user_id=user_id,
            name=clean_name,
            avatar_file_id=avatar_file_id,
            config=config,
            created_at=now,
        )

    async def delete(self, user_id: int, favorite_id: int) -> bool:
        assert self._conn
        cursor = await self._conn.execute(
            "DELETE FROM favorites WHERE user_id = ? AND id = ?",
            (user_id, favorite_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def update_file_id(self, favorite_id: int, avatar_file_id: str) -> None:
        assert self._conn
        await self._conn.execute(
            "UPDATE favorites SET avatar_file_id = ? WHERE id = ?",
            (avatar_file_id, favorite_id),
        )
        await self._conn.commit()

    @staticmethod
    def _row_to_favorite(row: aiosqlite.Row) -> Favorite:
        config_data = json.loads(row["config_json"])
        return Favorite(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            name=str(row["name"]),
            avatar_file_id=str(row["avatar_file_id"]),
            config=AvatarConfig.from_dict(config_data),
            created_at=str(row["created_at"]),
        )
