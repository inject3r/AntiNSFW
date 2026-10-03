from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

import mysql.connector
from mysql.connector import Error

from .config import (
    CACHE_MAX_ENTRIES,
    DATABASE_SCHEMA,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    DEFAULT_ACTION,
    DEFAULT_LANGUAGE,
    DEFAULT_MUTE_MINUTES,
    DEFAULT_THRESHOLD,
    DEFAULT_WARN_LIMIT,
    LANGUAGES,
    MODERATE_ADMINS_DEFAULT,
)

class Row(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

class Result:
    def __init__(self, cursor):
        self.rowcount = cursor.rowcount
        self._rows = [Row(row) for row in cursor.fetchall()] if cursor.description else []

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows = self._rows
        self._rows = []
        return rows

class Connection:
    def __init__(self, connection):
        self.connection = connection

    def _sql(self, sql: str) -> str:
        sql = sql.replace("?", "%s")
        sql = sql.replace("INSERT OR IGNORE", "INSERT IGNORE")
        sql = sql.replace("CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP")
        sql = __import__("re").sub(r"\bexcluded\.([A-Za-z_][A-Za-z0-9_]*)", r"VALUES(\1)", sql)
        return sql

    def execute(self, sql: str, params=()):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(self._sql(sql), params)
        return Result(cursor)

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()

class Database:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.conn = Connection(self._connect())
        self._init()

    def _connect(self):
        kwargs = {
            "host": DB_HOST,
            "port": DB_PORT,
            "user": DB_USER,
            "password": DB_PASSWORD,
            "database": DB_NAME,
            "charset": "utf8mb4",
            "autocommit": False,
        }
        try:
            return mysql.connector.connect(**kwargs)
        except Error as exc:
            if getattr(exc, "errno", None) != 1049:
                raise
            bootstrap = dict(kwargs)
            bootstrap.pop("database")
            connection = mysql.connector.connect(**bootstrap)
            cursor = connection.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            connection.commit()
            cursor.close()
            connection.close()
            return mysql.connector.connect(**kwargs)

    def _init(self):
        schema = DATABASE_SCHEMA.read_text(encoding="utf-8")
        statements = [item.strip() for item in schema.split(";") if item.strip()]
        for statement in statements:
            self.conn.execute(statement)
        self.conn.commit()

    async def upsert_user(
        self,
        user_id: int,
        language: Optional[str] = None,
        is_bot: bool = False,
        started: Optional[bool] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> None:

        async with self.lock:

            if language in LANGUAGES:

                self.conn.execute(
                    """
                    INSERT INTO users(user_id, language, language_selected, started, is_bot, username, first_name, last_name)
                    VALUES(?, ?, 1, ?, ?, ?, ?, ?)

                    ON DUPLICATE KEY UPDATE
                        language=VALUES(language),
                        language_selected=1,
                        started=CASE WHEN VALUES(started)=1 THEN 1 ELSE users.started END,
                        username=COALESCE(VALUES(username), users.username),
                        first_name=COALESCE(VALUES(first_name), users.first_name),
                        last_name=COALESCE(VALUES(last_name), users.last_name),
                        last_seen=CURRENT_TIMESTAMP
                    """,
                    (
                        user_id,
                        language,
                        int(bool(started)),
                        int(is_bot),
                        username,
                        first_name,
                        last_name,
                    ),
                )

            else:

                self.conn.execute(
                    """
                    INSERT INTO users(user_id, started, is_bot, username, first_name, last_name)
                    VALUES(?, ?, ?, ?, ?, ?)

                    ON DUPLICATE KEY UPDATE
                        started=CASE WHEN VALUES(started)=1 THEN 1 ELSE users.started END,
                        username=COALESCE(VALUES(username), users.username),
                        first_name=COALESCE(VALUES(first_name), users.first_name),
                        last_name=COALESCE(VALUES(last_name), users.last_name),
                        last_seen=CURRENT_TIMESTAMP
                    """,
                    (
                        user_id,
                        int(bool(started)),
                        int(is_bot),
                        username, first_name, last_name,
                    ),
                )

            self.conn.commit()

    async def get_user_language(
        self,
        user_id: int,
    ) -> str:

        async with self.lock:

            row = self.conn.execute(
                """
                SELECT language
                FROM users
                WHERE user_id=?
                """,
                (
                    user_id,
                ),
            ).fetchone()

            if (
                row
                and row["language"]
                in LANGUAGES
            ):
                return row["language"]

            return DEFAULT_LANGUAGE

    async def ensure_chat(
        self,
        chat_id: int,
        title: str = "",
        chat_type: str = "group",
    ) -> dict[str, Any]:

        async with self.lock:

            self.conn.execute(
                """
                INSERT INTO chats(
                    chat_id,
                    title,
                    chat_type,
                    language,
                    enabled,
                    bot_in_chat,
                    moderate_admins,
                    threshold,
                    action,
                    warn_limit,
                    escalation,
                    mute_minutes
                )
                VALUES(
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )

                ON DUPLICATE KEY UPDATE
                    title=VALUES(title),
                    chat_type=VALUES(chat_type),
                    bot_in_chat=1,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    chat_id,
                    title,
                    chat_type,
                    DEFAULT_LANGUAGE,
                    1,
                    1,
                    MODERATE_ADMINS_DEFAULT,
                    DEFAULT_THRESHOLD,
                    (
                        DEFAULT_ACTION
                        if DEFAULT_ACTION in ACTIONS
                        else "delete"
                    ),
                    DEFAULT_WARN_LIMIT,
                    "none",
                    DEFAULT_MUTE_MINUTES,
                ),
            )

            self.conn.commit()

            row = self.conn.execute(
                """
                SELECT *
                FROM chats
                WHERE chat_id=?
                """,
                (
                    chat_id,
                ),
            ).fetchone()

            return dict(row)

    async def get_chat(
        self,
        chat_id: int,
    ) -> Optional[dict[str, Any]]:

        async with self.lock:

            row = self.conn.execute(
                """
                SELECT *
                FROM chats
                WHERE chat_id=?
                """,
                (
                    chat_id,
                ),
            ).fetchone()

            return (
                dict(row)
                if row
                else None
            )

    async def set_chat(
        self,
        chat_id: int,
        **changes: Any,
    ) -> dict[str, Any]:

        allowed = {
            "language",
            "enabled",
            "bot_in_chat",
            "moderate_admins",
            "threshold",
            "action",
            "warn_limit",
            "escalation",
            "mute_minutes",
            "custom_message",
        }

        changes = {
            key: value
            for key, value in changes.items()
            if key in allowed
        }

        if not changes:
            chat = await self.get_chat(
                chat_id
            )

            return chat or {}

        async with self.lock:

            cols = ", ".join(
                f"{key}=?"
                for key in changes
            )

            values = [
                *changes.values(),
                chat_id,
            ]

            self.conn.execute(
                f"""
                UPDATE chats
                SET {cols},
                    updated_at=CURRENT_TIMESTAMP
                WHERE chat_id=?
                """,
                values,
            )

            self.conn.commit()

            row = self.conn.execute(
                """
                SELECT *
                FROM chats
                WHERE chat_id=?
                """,
                (
                    chat_id,
                ),
            ).fetchone()

            return dict(row)

    async def get_cached_detection(
        self,
        media_key: str,
        detector_signature: str,
        content_sha256: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:

        async with self.lock:

            row = self.conn.execute(
                """
                SELECT *
                FROM detections
                WHERE media_key=?
                  AND detector_signature=?
                LIMIT 1
                """,
                (
                    media_key,
                    detector_signature,
                ),
            ).fetchone()

            if row:

                self.conn.execute(
                    """
                    UPDATE detections
                    SET last_used_at=CURRENT_TIMESTAMP
                    WHERE media_key=?
                    """,
                    (
                        media_key,
                    ),
                )

                return dict(row)

            if content_sha256:

                row = self.conn.execute(
                    """
                    SELECT *
                    FROM detections
                    WHERE content_sha256=?
                      AND detector_signature=?
                    ORDER BY last_used_at DESC
                    LIMIT 1
                    """,
                    (
                        content_sha256,
                        detector_signature,
                    ),
                ).fetchone()

                if row:

                    self.conn.execute(
                        """
                        UPDATE detections
                        SET last_used_at=CURRENT_TIMESTAMP
                        WHERE media_key=?
                        """,
                        (
                            row["media_key"],
                        ),
                    )

                    return dict(row)

        return None

    async def save_detection(
        self,
        media_key: str,
        content_sha256: str,
        nsfw: bool,
        confidence: float,
        kind: str,
        detector_signature: str,
    ) -> None:

        async with self.lock:

            self.conn.execute(
                """
                INSERT INTO detections(
                    media_key,
                    content_sha256,
                    detector_signature,
                    nsfw,
                    confidence,
                    kind,
                    checked_at,
                    last_used_at
                )
                VALUES(
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )

                ON DUPLICATE KEY UPDATE
                    content_sha256=VALUES(content_sha256),
                    detector_signature=VALUES(detector_signature),
                    nsfw=VALUES(nsfw),
                    confidence=VALUES(confidence),
                    kind=VALUES(kind),
                    checked_at=CURRENT_TIMESTAMP,
                    last_used_at=CURRENT_TIMESTAMP
                """,
                (
                    media_key,
                    content_sha256,
                    detector_signature,
                    int(nsfw),
                    float(confidence),
                    kind,
                ),
            )

            self.conn.execute(
                """
                UPDATE stats
                SET value=value+1
                WHERE `stat_key`='checked'
                """
            )

            if nsfw:

                self.conn.execute(
                    """
                    UPDATE stats
                    SET value=value+1
                    WHERE `stat_key`='nsfw'
                    """
                )

            count = self.conn.execute(
                """
                SELECT COUNT(*)
                FROM detections
                """
            ).fetchone()[0]

            if count > CACHE_MAX_ENTRIES:

                excess = max(
                    100,
                    count - CACHE_MAX_ENTRIES,
                )

                self.conn.execute(
                    """
                    DELETE d FROM detections AS d
                    INNER JOIN (
                        SELECT media_key
                        FROM detections
                        ORDER BY last_used_at ASC
                        LIMIT ?
                    ) AS old ON old.media_key = d.media_key
                    """,
                    (
                        excess,
                    ),
                )

            self.conn.commit()

    async def add_warning(
        self,
        chat_id: int,
        user_id: int,
    ) -> int:

        async with self.lock:

            self.conn.execute(
                """
                INSERT INTO warnings(
                    chat_id,
                    user_id,
                    count
                )
                VALUES(?, ?, 1)

                ON DUPLICATE KEY UPDATE
                    count=count+1,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    chat_id,
                    user_id,
                ),
            )

            self.conn.commit()

            row = self.conn.execute(
                """
                SELECT count
                FROM warnings
                WHERE chat_id=?
                  AND user_id=?
                """,
                (
                    chat_id,
                    user_id,
                ),
            ).fetchone()

            return (
                int(row["count"])
                if row
                else 0
            )

    async def reset_warnings(
        self,
        chat_id: int,
        user_id: int,
    ) -> None:

        async with self.lock:

            self.conn.execute(
                """
                DELETE FROM warnings
                WHERE chat_id=?
                  AND user_id=?
                """,
                (
                    chat_id,
                    user_id,
                ),
            )

            self.conn.commit()

    async def get_stats(
        self,
    ) -> dict[str, int]:

        async with self.lock:

            def n(sql: str) -> int:
                return int(
                    self.conn.execute(
                        sql
                    ).fetchone()[0]
                )

            return {
                "checked": n(
                    """
                    SELECT value
                    FROM stats
                    WHERE `stat_key`='checked'
                    """
                ),
                "nsfw": n(
                    """
                    SELECT value
                    FROM stats
                    WHERE `stat_key`='nsfw'
                    """
                ),
                "groups": n(
                    """
                    SELECT COUNT(*)
                    FROM chats
                    WHERE enabled=1
                    """
                ),
                "users": n(
                    """
                    SELECT COUNT(*)
                    FROM users
                    """
                ),
            }

    async def user_language_selected(self, user_id: int) -> bool:
        async with self.lock:
            row = self.conn.execute("SELECT language_selected FROM users WHERE user_id=?", (user_id,)).fetchone()
            return bool(row and row["language_selected"])

    async def set_exempt_user(self, chat_id: int, user_id: int, added_by: int) -> None:
        async with self.lock:
            self.conn.execute("INSERT INTO exempt_users(chat_id,user_id,added_by) VALUES(?,?,?) ON DUPLICATE KEY UPDATE added_by=VALUES(added_by), added_at=CURRENT_TIMESTAMP", (chat_id,user_id,added_by))
            self.conn.commit()

    async def remove_exempt_user(self, chat_id: int, user_id: int) -> None:
        async with self.lock:
            self.conn.execute("DELETE FROM exempt_users WHERE chat_id=? AND user_id=?", (chat_id,user_id))
            self.conn.commit()

    async def is_exempt_user(self, chat_id: int, user_id: int) -> bool:
        async with self.lock:
            return bool(self.conn.execute("SELECT 1 FROM exempt_users WHERE chat_id=? AND user_id=? LIMIT 1", (chat_id,user_id)).fetchone())

    async def exempt_count(self, chat_id: int) -> int:
        async with self.lock:
            return int(self.conn.execute("SELECT COUNT(*) FROM exempt_users WHERE chat_id=?", (chat_id,)).fetchone()[0])

    async def block_media(self, chat_id: int, media_key: str, kind: str, blocked_by: int, content_sha256: Optional[str] = None) -> None:
        async with self.lock:
            self.conn.execute("INSERT INTO blocked_media(chat_id,media_key,content_sha256,kind,blocked_by) VALUES(?,?,?,?,?) ON DUPLICATE KEY UPDATE content_sha256=VALUES(content_sha256), kind=VALUES(kind), blocked_by=VALUES(blocked_by), blocked_at=CURRENT_TIMESTAMP", (chat_id,media_key,content_sha256,kind,blocked_by))
            self.conn.commit()

    async def unblock_media(self, chat_id: int, media_key: str) -> None:
        async with self.lock:
            self.conn.execute("DELETE FROM blocked_media WHERE chat_id=? AND media_key=?", (chat_id,media_key))
            self.conn.commit()

    async def is_media_blocked(self, chat_id: int, media_key: str, content_sha256: Optional[str] = None) -> bool:
        async with self.lock:
            if content_sha256:
                return bool(self.conn.execute("SELECT 1 FROM blocked_media WHERE chat_id=? AND (media_key=? OR content_sha256=?) LIMIT 1", (chat_id,media_key,content_sha256)).fetchone())
            return bool(self.conn.execute("SELECT 1 FROM blocked_media WHERE chat_id=? AND media_key=? LIMIT 1", (chat_id,media_key)).fetchone())

    async def get_detection_hash(self, media_key: str) -> Optional[str]:
        async with self.lock:
            row=self.conn.execute("SELECT content_sha256 FROM detections WHERE media_key=? LIMIT 1",(media_key,)).fetchone()
            return str(row[0]) if row and row[0] else None

    async def blocked_count(self, chat_id: Optional[int] = None) -> int:
        async with self.lock:
            if chat_id is None:
                return int(self.conn.execute("SELECT COUNT(*) FROM blocked_media").fetchone()[0])
            return int(self.conn.execute("SELECT COUNT(*) FROM blocked_media WHERE chat_id=?", (chat_id,)).fetchone()[0])

    async def record_chat_check(self, chat_id: int, nsfw: bool) -> None:
        async with self.lock:
            self.conn.execute("INSERT INTO chat_stats(chat_id,checked,nsfw) VALUES(?,?,?) ON DUPLICATE KEY UPDATE checked=checked+1, nsfw=nsfw+VALUES(nsfw), updated_at=CURRENT_TIMESTAMP", (chat_id,1,int(nsfw)))
            self.conn.execute("INSERT INTO daily_stats(chat_id,day,checked,nsfw) VALUES(?,?,?,?) ON DUPLICATE KEY UPDATE checked=checked+1, nsfw=nsfw+VALUES(nsfw)", (chat_id, time.strftime('%Y-%m-%d'),1,int(nsfw)))
            self.conn.execute("INSERT INTO stats(stat_key,value) VALUES('checked',1) ON DUPLICATE KEY UPDATE value=value+1")
            if nsfw:
                self.conn.execute("INSERT INTO stats(stat_key,value) VALUES('nsfw',1) ON DUPLICATE KEY UPDATE value=value+1")
            self.conn.commit()

    async def record_chat_action(self, chat_id: int, deleted: bool = False) -> None:
        async with self.lock:
            self.conn.execute("INSERT INTO chat_stats(chat_id,actions,deleted) VALUES(?,?,?) ON DUPLICATE KEY UPDATE actions=actions+1, deleted=deleted+VALUES(deleted), updated_at=CURRENT_TIMESTAMP", (chat_id,1,int(deleted)))
            self.conn.execute("INSERT INTO daily_stats(chat_id,day,actions,deleted) VALUES(?,?,?,?) ON DUPLICATE KEY UPDATE actions=actions+1, deleted=deleted+VALUES(deleted)", (chat_id, time.strftime('%Y-%m-%d'),1,int(deleted)))
            self.conn.commit()

    async def get_chat_stats(self, chat_id: int) -> dict[str,int]:
        async with self.lock:
            row=self.conn.execute("SELECT checked,nsfw,actions,deleted FROM chat_stats WHERE chat_id=?",(chat_id,)).fetchone()
            return dict(row) if row else {"checked":0,"nsfw":0,"actions":0,"deleted":0}

    async def list_active_groups(self) -> list[dict[str,Any]]:
        async with self.lock:
            rows=self.conn.execute("SELECT c.*, COALESCE(s.checked,0) checked, COALESCE(s.nsfw,0) nsfw, COALESCE(s.actions,0) actions, COALESCE(s.deleted,0) deleted FROM chats c LEFT JOIN chat_stats s ON s.chat_id=c.chat_id WHERE c.bot_in_chat=1 ORDER BY COALESCE(s.checked,0) DESC, c.updated_at DESC").fetchall()
            return [dict(r) for r in rows]

    async def list_started_user_ids(self) -> list[int]:
        async with self.lock:
            return [int(r[0]) for r in self.conn.execute("SELECT user_id FROM users WHERE started=1 AND is_bot=0 AND bot_blocked=0 ORDER BY last_seen DESC").fetchall()]

    async def track_chat_user(
        self,
        chat_id: int,
        user: dict[str, Any],
        message_id: Optional[int] = None,
    ) -> None:
        uid = int(user.get("id") or 0)
        if not uid:
            return
        async with self.lock:
            self.conn.execute(
                """
                INSERT INTO chat_users(
                    chat_id, user_id, username, first_name, last_name,
                    is_bot, message_count, last_message_id
                ) VALUES(?,?,?,?,?,?,1,?)
                ON DUPLICATE KEY UPDATE
                    username=VALUES(username),
                    first_name=VALUES(first_name),
                    last_name=VALUES(last_name),
                    is_bot=VALUES(is_bot),
                    message_count=chat_users.message_count+1,
                    last_message_id=VALUES(last_message_id),
                    last_seen=CURRENT_TIMESTAMP
                """,
                (
                    chat_id,
                    uid,
                    user.get("username"),
                    user.get("first_name"),
                    user.get("last_name"),
                    int(bool(user.get("is_bot"))),
                    int(message_id) if message_id else None,
                ),
            )
            self.conn.commit()

    async def list_user_groups(self, user_id:int, page:int=0, per_page:int=8) -> tuple[list[dict[str,Any]], int]:
        page=max(0,int(page)); per_page=max(1,min(50,int(per_page)))
        async with self.lock:
            total=int(self.conn.execute("SELECT COUNT(*) FROM chat_users WHERE user_id=?",(user_id,)).fetchone()[0])
            rows=self.conn.execute("SELECT c.chat_id,c.title,c.chat_type,c.bot_in_chat,cu.message_count,cu.first_seen,cu.last_seen FROM chat_users cu JOIN chats c ON c.chat_id=cu.chat_id WHERE cu.user_id=? ORDER BY cu.last_seen DESC LIMIT ? OFFSET ?",(user_id,per_page,page*per_page)).fetchall()
            return [dict(r) for r in rows], total

    async def list_tracked_chat_users(
        self,
        chat_id: int,
        page: int = 0,
        per_page: int = 8,
    ) -> list[dict[str, Any]]:
        page=max(0,int(page))
        per_page=max(1,min(20,int(per_page)))
        async with self.lock:
            rows=self.conn.execute(
                """
                SELECT * FROM chat_users
                WHERE chat_id=?
                ORDER BY is_bot ASC, last_seen DESC
                LIMIT ? OFFSET ?
                """,
                (chat_id,per_page,page*per_page),
            ).fetchall()
            return [dict(r) for r in rows]

    async def tracked_chat_user_count(self, chat_id: int) -> int:
        async with self.lock:
            return int(self.conn.execute(
                "SELECT COUNT(*) FROM chat_users WHERE chat_id=? AND is_bot=0",
                (chat_id,),
            ).fetchone()[0])

    async def tracked_chat_user_pages(self, chat_id: int, per_page: int = 8) -> int:
        n=await self.tracked_chat_user_count(chat_id)
        return max(1,(n+per_page-1)//per_page)

    async def owner_stats(self) -> dict[str,int]:
        async with self.lock:
            q=lambda sql:int(self.conn.execute(sql).fetchone()[0])
            return {"groups":q("SELECT COUNT(*) FROM chats"),"active_groups":q("SELECT COUNT(*) FROM chats WHERE bot_in_chat=1"),"users":q("SELECT COUNT(*) FROM users"),"started_users":q("SELECT COUNT(*) FROM users WHERE started=1 AND is_bot=0"),"blocked_users":q("SELECT COUNT(*) FROM users WHERE bot_blocked=1"),"exempt_users":q("SELECT COUNT(*) FROM exempt_users"),"blocked_media":q("SELECT COUNT(*) FROM blocked_media"),"checked":q("SELECT COALESCE(SUM(checked),0) FROM chat_stats"),"nsfw":q("SELECT COALESCE(SUM(nsfw),0) FROM chat_stats"),"actions":q("SELECT COALESCE(SUM(actions),0) FROM chat_stats")}

    async def list_users(self, page: int = 0, per_page: int = 10, search: str = "") -> tuple[list[dict[str, Any]], int]:
        page=max(0,int(page)); per_page=max(1,min(50,int(per_page))); search=(search or "").strip()
        async with self.lock:
            where=""; params=[]
            if search:
                where="WHERE CAST(user_id AS TEXT)=? OR username LIKE ? OR first_name LIKE ? OR last_name LIKE ?"
                params=[search, f"%{search.lstrip('@')}%", f"%{search}%", f"%{search}%"]
            total=int(self.conn.execute(f"SELECT COUNT(*) FROM users {where}",tuple(params)).fetchone()[0])
            rows=self.conn.execute(f"SELECT * FROM users {where} ORDER BY last_seen DESC LIMIT ? OFFSET ?",tuple(params+[per_page,page*per_page])).fetchall()
            return [dict(r) for r in rows], total

    async def get_user(self, user_id:int) -> Optional[dict[str,Any]]:
        async with self.lock:
            row=self.conn.execute("SELECT * FROM users WHERE user_id=?",(user_id,)).fetchone()
            return dict(row) if row else None

    async def get_user_summary(self, user_id: int) -> Optional[dict[str, Any]]:
        async with self.lock:
            user = self.conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
            if not user:
                return None
            chat_row = self.conn.execute(
                "SELECT COUNT(*) groups_count, COALESCE(SUM(message_count),0) messages_count FROM chat_users WHERE user_id=?",
                (user_id,),
            ).fetchone()
            warn_row = self.conn.execute(
                "SELECT COALESCE(SUM(count),0) warning_count, COUNT(*) warning_groups FROM warnings WHERE user_id=? AND count>0",
                (user_id,),
            ).fetchone()
            exempt_row = self.conn.execute(
                "SELECT COUNT(*) FROM exempt_users WHERE user_id=?",
                (user_id,),
            ).fetchone()
            audit_row = self.conn.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE actor_id=? OR details LIKE ?",
                (user_id, f"%user_id={user_id}%"),
            ).fetchone()
            return {
                **dict(user),
                "groups_count": int(chat_row["groups_count"] or 0),
                "messages_count": int(chat_row["messages_count"] or 0),
                "warning_count": int(warn_row["warning_count"] or 0),
                "warning_groups": int(warn_row["warning_groups"] or 0),
                "exempt_count": int(exempt_row[0] or 0),
                "audit_count": int(audit_row[0] or 0),
            }

    async def is_user_blocked(self, user_id: int) -> bool:
        async with self.lock:
            row = self.conn.execute("SELECT bot_blocked FROM users WHERE user_id=?", (user_id,)).fetchone()
            return bool(row[0]) if row else False

    async def set_user_blocked(self, user_id: int, blocked: bool) -> None:
        async with self.lock:
            self.conn.execute(
                "INSERT INTO users(user_id, bot_blocked, started) VALUES(?,?,0) ON DUPLICATE KEY UPDATE bot_blocked=?, last_seen=CURRENT_TIMESTAMP",
                (user_id, int(blocked), int(blocked)),
            )
            self.conn.commit()

    async def set_user_note(self, user_id: int, note: str) -> None:
        async with self.lock:
            self.conn.execute(
                "INSERT INTO users(user_id, owner_note) VALUES(?,?) ON DUPLICATE KEY UPDATE owner_note=?, last_seen=CURRENT_TIMESTAMP",
                (user_id, note[:1200], note[:1200]),
            )
            self.conn.commit()

    async def reset_user_warnings(self, user_id: int, chat_id: Optional[int] = None) -> int:
        async with self.lock:
            if chat_id is None:
                cur = self.conn.execute("DELETE FROM warnings WHERE user_id=?", (user_id,))
            else:
                cur = self.conn.execute("DELETE FROM warnings WHERE user_id=? AND chat_id=?", (user_id, chat_id))
            self.conn.commit()
            return int(cur.rowcount if cur.rowcount is not None else 0)

    async def list_user_warnings(self, user_id: int, page: int = 0, per_page: int = 8) -> tuple[list[dict[str, Any]], int]:
        page=max(0,int(page)); per_page=max(1,min(20,int(per_page)))
        async with self.lock:
            total=int(self.conn.execute("SELECT COUNT(*) FROM warnings WHERE user_id=? AND count>0", (user_id,)).fetchone()[0])
            rows=self.conn.execute("""
                SELECT w.chat_id, w.user_id, w.count, w.updated_at,
                       c.title, c.chat_type, c.bot_in_chat, c.enabled
                FROM warnings w LEFT JOIN chats c ON c.chat_id=w.chat_id
                WHERE w.user_id=? AND w.count>0
                ORDER BY w.updated_at DESC
                LIMIT ? OFFSET ?
            """, (user_id, per_page, page*per_page)).fetchall()
            return [dict(r) for r in rows], total

    async def list_user_exemptions(self, user_id: int, page: int = 0, per_page: int = 8) -> tuple[list[dict[str, Any]], int]:
        page=max(0,int(page)); per_page=max(1,min(20,int(per_page)))
        async with self.lock:
            total=int(self.conn.execute("SELECT COUNT(*) FROM exempt_users WHERE user_id=?", (user_id,)).fetchone()[0])
            rows=self.conn.execute("""
                SELECT e.chat_id, e.user_id, e.added_by, e.added_at,
                       c.title, c.chat_type, c.bot_in_chat, c.enabled
                FROM exempt_users e LEFT JOIN chats c ON c.chat_id=e.chat_id
                WHERE e.user_id=?
                ORDER BY e.added_at DESC
                LIMIT ? OFFSET ?
            """, (user_id, per_page, page*per_page)).fetchall()
            return [dict(r) for r in rows], total

    async def list_user_audit_logs(self, user_id: int, page: int = 0, per_page: int = 8) -> tuple[list[dict[str, Any]], int]:
        page=max(0,int(page)); per_page=max(1,min(20,int(per_page)))
        needle=f"%user_id={user_id}%"
        async with self.lock:
            total=int(self.conn.execute("SELECT COUNT(*) FROM audit_logs WHERE actor_id=? OR details LIKE ?", (user_id, needle)).fetchone()[0])
            rows=self.conn.execute("""
                SELECT * FROM audit_logs
                WHERE actor_id=? OR details LIKE ?
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """, (user_id, needle, per_page, page*per_page)).fetchall()
            return [dict(r) for r in rows], total

    async def list_exempt_users(self, chat_id:int, page:int=0, per_page:int=10) -> tuple[list[dict[str,Any]], int]:
        page=max(0,int(page)); per_page=max(1,min(50,int(per_page)))
        async with self.lock:
            total=int(self.conn.execute("SELECT COUNT(*) FROM exempt_users WHERE chat_id=?",(chat_id,)).fetchone()[0])
            rows=self.conn.execute("""SELECT e.*, cu.username, cu.first_name, cu.last_name, cu.message_count, cu.last_seen
                FROM exempt_users e LEFT JOIN chat_users cu ON cu.chat_id=e.chat_id AND cu.user_id=e.user_id
                WHERE e.chat_id=? ORDER BY e.added_at DESC LIMIT ? OFFSET ?""",(chat_id,per_page,page*per_page)).fetchall()
            return [dict(r) for r in rows], total

    async def list_blocked_media(self, chat_id:int, page:int=0, per_page:int=8) -> tuple[list[dict[str,Any]], int]:
        page=max(0,int(page)); per_page=max(1,min(50,int(per_page)))
        async with self.lock:
            total=int(self.conn.execute("SELECT COUNT(*) FROM blocked_media WHERE chat_id=?",(chat_id,)).fetchone()[0])
            rows=self.conn.execute("SELECT * FROM blocked_media WHERE chat_id=? ORDER BY blocked_at DESC LIMIT ? OFFSET ?",(chat_id,per_page,page*per_page)).fetchall()
            return [dict(r) for r in rows], total

    async def list_audit_logs(self, chat_id:Optional[int]=None, page:int=0, per_page:int=10) -> tuple[list[dict[str,Any]], int]:
        page=max(0,int(page)); per_page=max(1,min(50,int(per_page)))
        async with self.lock:
            if chat_id is None:
                total=int(self.conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0])
                rows=self.conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ? OFFSET ?",(per_page,page*per_page)).fetchall()
            else:
                total=int(self.conn.execute("SELECT COUNT(*) FROM audit_logs WHERE chat_id=?",(chat_id,)).fetchone()[0])
                rows=self.conn.execute("SELECT * FROM audit_logs WHERE chat_id=? ORDER BY id DESC LIMIT ? OFFSET ?",(chat_id,per_page,page*per_page)).fetchall()
            return [dict(r) for r in rows], total

    async def audit(self, event_type:str, chat_id:Optional[int]=None, actor_id:Optional[int]=None, actor_name:str="", details:str="") -> None:
        async with self.lock:
            self.conn.execute("INSERT INTO audit_logs(chat_id,actor_id,actor_name,event_type,details) VALUES(?,?,?,?,?)",(chat_id,actor_id,actor_name,event_type,details[:1800]))
            self.conn.commit()

    async def period_stats(self, days:int) -> dict[str,int]:
        from datetime import date, timedelta
        days=max(1,int(days))
        cutoff=(date.today() - timedelta(days=days-1)).isoformat()
        async with self.lock:
            row=self.conn.execute("""SELECT COALESCE(SUM(checked),0) checked, COALESCE(SUM(nsfw),0) nsfw, COALESCE(SUM(actions),0) actions, COALESCE(SUM(deleted),0) deleted
                FROM daily_stats WHERE day >= ?""",(cutoff,)).fetchone()
            return {k:int(row[k] or 0) for k in ('checked','nsfw','actions','deleted')}

    async def mark_chat_membership(self, chat_id:int, in_chat:bool) -> None:
        async with self.lock:
            self.conn.execute("UPDATE chats SET bot_in_chat=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?",(int(in_chat),chat_id))
            self.conn.commit()

    async def checkpoint(
        self,
    ) -> None:

        async with self.lock:

            self.conn.commit()

            self.conn.execute(
                "PRAGMA wal_checkpoint(TRUNCATE)"
            )

            self.conn.commit()

    def close(
        self,
    ) -> None:

        self.conn.commit()
        self.conn.close()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()
