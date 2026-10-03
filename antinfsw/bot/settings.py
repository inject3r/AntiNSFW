from __future__ import annotations

import asyncio
import logging
import os
import platform
import re
import time
from collections import OrderedDict
from typing import Any, Optional

try:
    import resource
except ImportError:
    resource = None

from PIL import Image, UnidentifiedImageError

from ..common import MediaRef, esc, t
from ..config import *
from ..database import Database
from ..detector import ModelDetector, extract_media_frames, media_from_message, command_of, mention_html, _resize_frame, av
from ..telegram import TelegramAPI
from ..ui import settings_keyboard, settings_text

class SettingsMixin:
            async def show_settings(
                self,
                chat_id: int,
                lang: Optional[str] = None,
                message_id: Optional[int] = None,
            ) -> None:

                chat = (
                    await self.db.get_chat(
                        chat_id
                    )
                )

                if not chat:

                    chat = (
                        await self.db.ensure_chat(
                            chat_id
                        )
                    )

                lang = (
                    lang
                    or chat["language"]
                )

                text = settings_text(
                    chat,
                    lang,
                )

                kwargs = {
                    "parse_mode": "HTML",
                    "reply_markup": settings_keyboard(
                        chat,
                        lang,
                    ),
                    "disable_web_page_preview": True,
                }

                if message_id:

                    await self.api.edit_message(
                        chat_id,
                        message_id,
                        text,
                        **kwargs,
                    )

                else:

                    await self.api.send_message(
                        chat_id,
                        text,
                        **kwargs,
                    )

            async def handle_settings(
                self,
                message: dict[str, Any],
            ) -> None:

                group, lang = (
                    await self.require_admin(
                        message
                    )
                )

                if not group:
                    return

                await self.show_settings(
                    message["chat"]["id"],
                    group["language"],
                )

            async def handle_setmessage(
                self,
                message: dict[str, Any],
                arg: str,
            ) -> None:

                group, lang = (
                    await self.require_admin(
                        message
                    )
                )

                if not group:
                    return

                chat_id = message[
                    "chat"
                ]["id"]

                if not arg:

                    await self.api.send_message(
                        chat_id,
                        t(
                            lang,
                            "custom_help",
                        ),
                    )

                    return

                if len(arg) > 900:

                    await self.api.send_message(
                        chat_id,
                        t(
                            lang,
                            "custom_help",
                        ),
                    )

                    return

                await self.db.set_chat(
                    chat_id,
                    custom_message=arg,
                )

                await self.api.send_message(
                    chat_id,
                    t(
                        lang,
                        "custom_saved",
                    ),
                )

            async def handle_stats(
                self,
                message: dict[str, Any],
            ) -> None:

                chat = message.get(
                    "chat",
                    {},
                )

                user = message.get(
                    "from",
                    {},
                )

                uid = int(
                    user["id"]
                )

                if chat.get(
                    "type"
                ) in {
                    "group",
                    "supergroup",
                }:

                    group = (
                        await self.db.get_chat(
                            int(chat["id"])
                        )
                        or
                        await self.db.ensure_chat(
                            int(chat["id"]),
                            chat.get(
                                "title",
                                "",
                            ),
                            chat.get(
                                "type",
                                "group",
                            ),
                        )
                    )

                    if not await self.is_group_admin(
                        int(chat["id"]),
                        uid,
                    ):

                        await self.api.send_message(
                            chat["id"],
                            t(
                                group["language"],
                                "admin_only",
                            ),
                        )

                        return

                    lang = group[
                        "language"
                    ]

                else:

                    lang = (
                        await self.db.get_user_language(
                            uid
                        )
                    )

                stats = (
                    await self.db.get_stats()
                )

                await self.api.send_message(
                    chat["id"],
                    t(
                        lang,
                        "stats",
                        **stats,
                    ),
                )

            async def handle_help(
                self,
                message: dict[str, Any],
            ) -> None:

                chat = message.get(
                    "chat",
                    {},
                )

                uid = int(
                    message.get(
                        "from",
                        {},
                    ).get(
                        "id",
                        0,
                    )
                )

                lang = (
                    await self.db.get_user_language(
                        uid
                    )
                )

                if chat.get(
                    "type"
                ) in {
                    "group",
                    "supergroup",
                }:

                    group = (
                        await self.db.get_chat(
                            int(chat["id"])
                        )
                    )

                    if group:
                        lang = group[
                            "language"
                        ]

                await self.api.send_message(
                    chat["id"],
                    t(
                        lang,
                        "help",
                    ),
                )

            async def settings_callback(
                self,
                callback: dict[str, Any],
            ) -> None:

                message = callback.get(
                    "message",
                    {},
                )

                user = callback.get(
                    "from",
                    {},
                )

                chat = message.get(
                    "chat",
                    {},
                )

                if chat.get(
                    "type"
                ) not in {
                    "group",
                    "supergroup",
                }:

                    await self.api.answer_callback(
                        callback["id"],
                        "Group only",
                    )

                    return

                chat_id = int(
                    chat["id"]
                )

                uid = int(
                    user["id"]
                )

                if not await self.is_group_admin(
                    chat_id,
                    uid,
                ):

                    await self.api.answer_callback(
                        callback["id"],
                        "Admin only",
                    )

                    return

                group = (
                    await self.db.ensure_chat(
                        chat_id,
                        chat.get(
                            "title",
                            "",
                        ),
                        chat.get(
                            "type",
                            "group",
                        ),
                    )
                )

                lang = group[
                    "language"
                ]

                data = callback.get(
                    "data",
                    "",
                )

                await self.api.answer_callback(
                    callback["id"]
                )

                if data == "s:toggle":

                    group = (
                        await self.db.set_chat(
                            chat_id,
                            enabled=(
                                0
                                if group["enabled"]
                                else 1
                            ),
                        )
                    )

                    await self.show_settings(
                        chat_id,
                        group["language"],
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                    )

                    return

                if data == "s:lang":

                    rows = []

                    for code, info in (
                        LANGUAGES.items()
                    ):

                        rows.append(
                            [
                                {
                                    "text": (
                                        f"{info['flag']} "
                                        f"{info['name']}"
                                    ),
                                    "callback_data": (
                                        f"s:lang:{code}"
                                    ),
                                }
                            ]
                        )

                    rows.append(
                        [
                            {
                                "text": t(
                                    lang,
                                    "btn_back",
                                ),
                                "callback_data": "s:back",
                            }
                        ]
                    )

                    await self.api.edit_message(
                        chat_id,
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                        t(
                            lang,
                            "pick_language",
                        ),
                        reply_markup={
                            "inline_keyboard": rows
                        },
                    )

                    return

                if data.startswith(
                    "s:lang:"
                ):

                    code = data.split(
                        ":"
                    )[-1]

                    if code in LANGUAGES:

                        group = (
                            await self.db.set_chat(
                                chat_id,
                                language=code,
                            )
                        )

                        await self.show_settings(
                            chat_id,
                            code,
                            int(
                                message[
                                    "message_id"
                                ]
                            ),
                        )

                    return

                if data == "s:threshold":

                    rows = []
                    vals = list(THRESHOLDS)
                    for i in range(0, len(vals), 5):
                        rows.append([
                            {"text": f"{v:.0%}", "callback_data": f"s:th:{v:.2f}"}
                            for v in vals[i:i+5]
                        ])

                    rows.append(
                        [
                            {
                                "text": t(
                                    lang,
                                    "btn_back",
                                ),
                                "callback_data": "s:back",
                            }
                        ]
                    )

                    await self.api.edit_message(
                        chat_id,
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                        t(
                            lang,
                            "pick_threshold",
                        ),
                        reply_markup={
                            "inline_keyboard": rows
                        },
                    )

                    return

                if data.startswith(
                    "s:th:"
                ):

                    value = float(
                        data.split(
                            ":"
                        )[-1]
                    )

                    if value in THRESHOLDS:

                        group = (
                            await self.db.set_chat(
                                chat_id,
                                threshold=value,
                            )
                        )

                        await self.show_settings(
                            chat_id,
                            group["language"],
                            int(
                                message[
                                    "message_id"
                                ]
                            ),
                        )

                    return

                if data == "s:action":

                    rows = [
                        [
                            {
                                "text": t(
                                    lang,
                                    f"action_{a}",
                                ),
                                "callback_data": (
                                    f"s:action:{a}"
                                ),
                            }
                        ]
                        for a in ACTIONS
                    ]

                    rows.append(
                        [
                            {
                                "text": t(
                                    lang,
                                    "btn_back",
                                ),
                                "callback_data": "s:back",
                            }
                        ]
                    )

                    await self.api.edit_message(
                        chat_id,
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                        t(
                            lang,
                            "pick_action",
                        ),
                        reply_markup={
                            "inline_keyboard": rows
                        },
                    )

                    return

                if data.startswith(
                    "s:action:"
                ):

                    action = data.split(
                        ":"
                    )[-1]

                    if action in ACTIONS:

                        group = (
                            await self.db.set_chat(
                                chat_id,
                                action=action,
                            )
                        )

                        await self.show_settings(
                            chat_id,
                            group["language"],
                            int(
                                message[
                                    "message_id"
                                ]
                            ),
                        )

                    return

                if data == "s:warn":

                    rows = [
                        [
                            {
                                "text": str(v),
                                "callback_data": (
                                    f"s:warn:{v}"
                                ),
                            }
                            for v in WARN_LIMITS
                        ]
                    ]

                    rows.append(
                        [
                            {
                                "text": t(
                                    lang,
                                    "btn_back",
                                ),
                                "callback_data": "s:back",
                            }
                        ]
                    )

                    await self.api.edit_message(
                        chat_id,
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                        t(
                            lang,
                            "pick_warn",
                        ),
                        reply_markup={
                            "inline_keyboard": rows
                        },
                    )

                    return

                if data.startswith(
                    "s:warn:"
                ):

                    value = int(
                        data.split(
                            ":"
                        )[-1]
                    )

                    if value in WARN_LIMITS:

                        group = (
                            await self.db.set_chat(
                                chat_id,
                                warn_limit=value,
                            )
                        )

                        await self.show_settings(
                            chat_id,
                            group["language"],
                            int(
                                message[
                                    "message_id"
                                ]
                            ),
                        )

                    return

                if data == "s:esc":

                    rows = [
                        [
                            {
                                "text": t(
                                    lang,
                                    f"esc_{e}",
                                ),
                                "callback_data": (
                                    f"s:esc:{e}"
                                ),
                            }
                        ]
                        for e in ESCALATIONS
                    ]

                    rows.append(
                        [
                            {
                                "text": t(
                                    lang,
                                    "btn_back",
                                ),
                                "callback_data": "s:back",
                            }
                        ]
                    )

                    await self.api.edit_message(
                        chat_id,
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                        t(
                            lang,
                            "pick_escalation",
                        ),
                        reply_markup={
                            "inline_keyboard": rows
                        },
                    )

                    return

                if data.startswith(
                    "s:esc:"
                ):

                    value = data.split(
                        ":"
                    )[-1]

                    if value in ESCALATIONS:

                        group = (
                            await self.db.set_chat(
                                chat_id,
                                escalation=value,
                            )
                        )

                        await self.show_settings(
                            chat_id,
                            group["language"],
                            int(
                                message[
                                    "message_id"
                                ]
                            ),
                        )

                    return

                if data == "s:mute":

                    rows = [
                        [
                            {
                                "text": f"{v} min",
                                "callback_data": (
                                    f"s:mute:{v}"
                                ),
                            }
                            for v in MUTE_DURATIONS[:3]
                        ],
                        [
                            {
                                "text": f"{v} min",
                                "callback_data": (
                                    f"s:mute:{v}"
                                ),
                            }
                            for v in MUTE_DURATIONS[3:]
                        ],
                    ]

                    rows.append(
                        [
                            {
                                "text": t(
                                    lang,
                                    "btn_back",
                                ),
                                "callback_data": "s:back",
                            }
                        ]
                    )

                    await self.api.edit_message(
                        chat_id,
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                        t(
                            lang,
                            "pick_mute",
                        ),
                        reply_markup={
                            "inline_keyboard": rows
                        },
                    )

                    return

                if data.startswith(
                    "s:mute:"
                ):

                    value = int(
                        data.split(
                            ":"
                        )[-1]
                    )

                    if value in MUTE_DURATIONS:

                        group = (
                            await self.db.set_chat(
                                chat_id,
                                mute_minutes=value,
                            )
                        )

                        await self.show_settings(
                            chat_id,
                            group["language"],
                            int(
                                message[
                                    "message_id"
                                ]
                            ),
                        )

                    return

                if data == "s:admins":
                    group=await self.db.set_chat(chat_id,moderate_admins=(0 if group.get("moderate_admins") else 1))
                    await self.show_settings(chat_id,group["language"],int(message["message_id"]))
                    return

                if data == "s:message":

                    await self.api.edit_message(
                        chat_id,
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                        t(
                            lang,
                            "custom_help",
                        ),
                        reply_markup={
                            "inline_keyboard": [
                                [
                                    {
                                        "text": t(
                                            lang,
                                            "btn_back",
                                        ),
                                        "callback_data": (
                                            "s:back"
                                        ),
                                    }
                                ]
                            ],
                        },
                    )

                    return

                if data == "s:reset":

                    group = (
                        await self.db.set_chat(
                            chat_id,
                            custom_message=None,
                        )
                    )

                    await self.api.edit_message(
                        chat_id,
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                        t(
                            group["language"],
                            "custom_reset",
                        ),
                        reply_markup={
                            "inline_keyboard": [
                                [
                                    {
                                        "text": t(
                                            group["language"],
                                            "btn_back",
                                        ),
                                        "callback_data": "s:back",
                                    }
                                ]
                            ],
                        },
                    )

                    return

                if data == "s:back":

                    await self.show_settings(
                        chat_id,
                        lang,
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                    )

                    return
