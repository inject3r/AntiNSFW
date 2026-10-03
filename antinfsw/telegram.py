from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from .config import BOT_TOKEN, TELEGRAM_API, TELEGRAM_FILE_API

class TelegramAPI:

    def __init__(self, token: str = BOT_TOKEN):

        timeout = httpx.Timeout(
            connect=15,
            read=65,
            write=30,
            pool=15,
        )

        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(
                max_connections=32,
                max_keepalive_connections=16,
            ),
        )

        self.token = token

        self.base = (
            f"https://api.telegram.org/bot{token}"
        )

        self.file_base = (
            f"https://api.telegram.org/file/bot{token}"
        )

    async def close(
        self,
    ) -> None:

        await self.client.aclose()

    async def call(
        self,
        method: str,
        payload: Optional[
            dict[str, Any]
        ] = None,
        timeout: Optional[
            float
        ] = None,
    ) -> Any:

        for attempt in range(5):

            try:
                request_payload = payload or {}
                logging.debug(
                    "API_CALL method=%s attempt=%d keys=%s",
                    method,
                    attempt + 1,
                    sorted(request_payload.keys()),
                )

                response = await self.client.post(
                    f"{self.base}/{method}",
                    json=request_payload,
                    timeout=timeout,
                )

                data = response.json()

                logging.debug(
                    "API_RESULT method=%s status=%s ok=%s error_code=%s",
                    method,
                    response.status_code,
                    data.get("ok"),
                    data.get("error_code"),
                )

                if data.get("ok"):
                    return data.get("result")

                if (
                    data.get("error_code")
                    == 429
                ):

                    retry = int(
                        data.get(
                            "parameters",
                            {},
                        ).get(
                            "retry_after",
                            2,
                        )
                    )

                    await asyncio.sleep(
                        min(
                            max(
                                retry,
                                1,
                            ),
                            60,
                        )
                    )

                    continue

                raise RuntimeError(
                    f"{method}: {data}"
                )

            except (
                httpx.HTTPError,
                RuntimeError,
            ) as exc:

                if attempt >= 4:
                    raise

                await asyncio.sleep(
                    min(
                        2 ** attempt,
                        8,
                    )
                )

                logging.warning(
                    "Telegram API retry %s after %s: %s",
                    method,
                    attempt + 1,
                    exc,
                )

        return None

    async def get_updates(
        self,
        offset: int,
    ) -> list[dict[str, Any]]:

        updates = (
            await self.call(
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 50,
                    "allowed_updates": [
                        "message",
                        "callback_query",
                        "my_chat_member",
                    ],
                },
                timeout=65,
            )
            or []
        )

        logging.debug(
            "POLL_RESULT offset=%s updates=%d",
            offset,
            len(updates),
        )
        return updates

    async def get_file_bytes(
        self,
        file_id: str,
    ) -> tuple[
        bytes,
        dict[str, Any],
    ]:

        meta = await self.call(
            "getFile",
            {
                "file_id": file_id,
            },
        )

        file_path = meta.get(
            "file_path"
        )

        if not file_path:
            raise RuntimeError(
                "Telegram returned no file_path"
            )

        reported_size = int(meta.get("file_size") or 0)
        if reported_size > MAX_MEDIA_BYTES:
            raise ValueError(
                f"file too large for Bot API download limit: {reported_size} bytes"
            )

        async with self.client.stream(
            "GET",
            f"{self.file_base}/{file_path}",
        ) as response:

            if response.status_code == 404:
                raise FileNotFoundError(file_path)

            response.raise_for_status()

            chunks: list[bytes] = []
            total = 0

            async for chunk in response.aiter_bytes(1024 * 1024):
                total += len(chunk)
                if total > MAX_MEDIA_BYTES:
                    raise ValueError(
                        "file too large for Bot API download limit"
                    )
                chunks.append(chunk)

        return b"".join(chunks), meta

    async def delete_message(
        self,
        chat_id: int,
        message_id: int,
    ) -> Any:

        return await self.call(
            "deleteMessage",
            {
                "chat_id": chat_id,
                "message_id": message_id,
            },
        )

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        **kwargs: Any,
    ) -> Any:

        payload = {
            "chat_id": chat_id,
            "text": text,
        }

        payload.update(
            kwargs
        )

        return await self.call(
            "sendMessage",
            payload,
        )

    async def copy_message(
        self,
        chat_id: int | str,
        from_chat_id: int | str,
        message_id: int,
    ) -> Any:
        return await self.call(
            "copyMessage",
            {"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id},
        )

    async def edit_message(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        **kwargs: Any,
    ) -> Any:

        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }

        payload.update(
            kwargs
        )

        return await self.call(
            "editMessageText",
            payload,
        )

    async def answer_callback(
        self,
        callback_id: str,
        text: str = "",
    ) -> Any:

        payload = {
            "callback_query_id": callback_id,
        }

        if text:
            payload["text"] = text

        return await self.call(
            "answerCallbackQuery",
            payload,
        )

    async def get_chat_member(
        self,
        chat_id: int,
        user_id: int,
    ) -> Any:

        return await self.call(
            "getChatMember",
            {
                "chat_id": chat_id,
                "user_id": user_id,
            },
        )

    async def restrict_member(
        self,
        chat_id: int,
        user_id: int,
        until_date: int,
    ) -> Any:

        return await self.call(
            "restrictChatMember",
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "permissions": {
                    "can_send_messages": False,
                    "can_send_audios": False,
                    "can_send_documents": False,
                    "can_send_photos": False,
                    "can_send_videos": False,
                    "can_send_video_notes": False,
                    "can_send_voice_notes": False,
                    "can_send_polls": False,
                    "can_send_other_messages": False,
                    "can_add_web_page_previews": False,
                    "can_change_info": False,
                    "can_invite_users": False,
                    "can_pin_messages": False,
                    "can_manage_topics": False,
                },
                "use_independent_chat_permissions": True,
                "until_date": until_date,
            },
        )

    async def ban_member(
        self,
        chat_id: int,
        user_id: int,
        until_date: Optional[int] = None,
    ) -> Any:

        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
        }

        if until_date is not None:
            payload[
                "until_date"
            ] = until_date

        return await self.call(
            "banChatMember",
            payload,
        )

    async def unban_member(
        self,
        chat_id: int,
        user_id: int,
    ) -> Any:

        return await self.call(
            "unbanChatMember",
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "only_if_banned": True,
            },
        )

    async def get_chat(
        self,
        chat_id: int | str,
    ) -> Any:
        return await self.call("getChat", {"chat_id": chat_id})

    async def get_chat_member_count(
        self,
        chat_id: int | str,
    ) -> int:
        return int(await self.call("getChatMemberCount", {"chat_id": chat_id}))

    async def get_chat_administrators(
        self,
        chat_id: int | str,
    ) -> list[dict[str, Any]]:
        return await self.call(
            "getChatAdministrators",
            {"chat_id": chat_id},
        ) or []

    async def set_my_commands(
        self,
    ) -> None:
        # Keep privileged/admin commands out of the normal command menu.
        public_commands = [
            {"command": "start", "description": "Start / language"},
            {"command": "help", "description": "Help"},
        ]
        await self.call(
            "setMyCommands",
            {"commands": public_commands},
        )

        # Owner-only menu.
        await self.call(
            "setMyCommands",
            {
                "scope": {"type": "chat", "chat_id": OWNER_ID},
                "commands": [
                    {"command": "owner", "description": "Owner dashboard"},
                    {"command": "test", "description": "Private detection test"},
                    {"command": "help", "description": "Help"},
                ],
            },
        )

        # Group-admin-only menu
        await self.call(
            "setMyCommands",
            {
                "scope": {"type": "all_chat_administrators"},
                "commands": [
                    {"command": "settings", "description": "Group settings"},
                    {"command": "stats", "description": "Group statistics"},
                    {"command": "free", "description": "Whitelist a user"},
                    {"command": "unfree", "description": "Remove a user from whitelist"},
                    {"command": "freelist", "description": "Whitelist status"},
                    {"command": "blockmedia", "description": "Block replied media"},
                    {"command": "unblockmedia", "description": "Unblock replied media"},
                    {"command": "groupstats", "description": "Group moderation stats"},
                    {"command": "setmessage", "description": "Set moderation message"},
                ],
            },
        )
