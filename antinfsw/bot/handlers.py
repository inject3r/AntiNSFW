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

class HandlersMixin:
            async def language_picker(
                self,
                chat_id: int,
                prompt_message_id: Optional[int] = None,
            ) -> None:

                buttons = []
                row = []

                for code, info in LANGUAGES.items():

                    row.append(
                        {
                            "text": (
                                f"{info['flag']} "
                                f"{info['name']}"
                            ),
                            "callback_data": (
                                f"lang:{code}"
                            ),
                        }
                    )

                    if len(row) == 2:

                        buttons.append(
                            row
                        )

                        row = []

                if row:
                    buttons.append(
                        row
                    )

                markup = {
                    "inline_keyboard": buttons
                }

                if prompt_message_id:

                    await self.api.edit_message(
                        chat_id,
                        prompt_message_id,
                        (
                            "🌐 "
                            +
                            t(
                                "en",
                                "start_choose",
                            )
                        ),
                        reply_markup=markup,
                    )

                else:

                    await self.api.send_message(
                        chat_id,
                        (
                            "🌐 "
                            +
                            t(
                                "en",
                                "start_choose",
                            )
                        ),
                        reply_markup=markup,
                    )

            async def send_start(
                self,
                chat_id: int,
                user_id: int,
            ) -> None:

                lang = (
                    await self.db.get_user_language(
                        user_id
                    )
                )

                add_url = (
                    f"https://t.me/"
                    f"{self.bot_username}"
                    f"?startgroup=true"
                )

                markup = {
                    "inline_keyboard": [
                        [
                            {
                                "text": t(
                                    lang,
                                    "add_group",
                                ),
                                "url": add_url,
                            }
                        ],
                        [
                            {
                                "text": (
                                    f"{LANGUAGES[lang]['flag']} "
                                    f"{LANGUAGES[lang]['name']}"
                                ),
                                "callback_data": (
                                    "start:language"
                                ),
                            }
                        ],
                        [
                            {
                                "text": "👨‍💻 توسعه‌دهنده" if lang == "fa" else "👨‍💻 Developer",
                                "url": "https://t.me/inject3r",
                            }
                        ],
                    ]
                }

                await self.api.send_message(
                    chat_id,
                    (
                        f"<b>{t(lang, 'start_title')}</b>"
                        f"\n\n"
                        f"{t(lang, 'start_body')}"
                    ),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=markup,
                )

            async def handle_start(
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

                if chat.get(
                    "type"
                ) != "private":
                    return

                user_id = int(
                    user["id"]
                )

                await self.db.upsert_user(
                    user_id,
                    is_bot=bool(user.get("is_bot")),
                    started=True,
                    username=user.get("username"),
                    first_name=user.get("first_name"),
                    last_name=user.get("last_name"),
                )

                if await self.db.user_language_selected(user_id):
                    await self.send_start(int(chat["id"]), user_id)
                    return

                await self.language_picker(int(chat["id"]))

            async def handle_language_callback(
                self,
                callback: dict[str, Any],
                code: str,
            ) -> None:

                user = callback.get(
                    "from",
                    {},
                )

                message = callback.get(
                    "message",
                    {},
                )

                uid = int(
                    user["id"]
                )

                chat_id = int(
                    message.get(
                        "chat",
                        {},
                    ).get(
                        "id"
                    )
                )

                await self.db.upsert_user(
                    uid,
                    language=code,
                    is_bot=bool(
                        user.get(
                            "is_bot"
                        )
                    ),
                )

                await self.api.answer_callback(
                    callback["id"]
                )

                if (
                    message.get(
                        "chat",
                        {},
                    ).get("type")
                    == "private"
                ):

                    add_url = (
                        f"https://t.me/"
                        f"{self.bot_username}"
                        f"?startgroup=true"
                    )

                    markup = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": t(
                                        code,
                                        "add_group",
                                    ),
                                    "url": add_url,
                                }
                            ],
                            [
                                {
                                    "text": (
                                        f"{LANGUAGES[code]['flag']} "
                                        f"{LANGUAGES[code]['name']}"
                                    ),
                                    "callback_data": (
                                        "start:language"
                                    ),
                                }
                            ],
                            [
                                {
                                    "text": "👨‍💻 توسعه‌دهنده" if code == "fa" else "👨‍💻 Developer",
                                    "url": "https://t.me/inject3r",
                                }
                            ],
                        ]
                    }

                    await self.api.edit_message(
                        chat_id,
                        int(
                            message[
                                "message_id"
                            ]
                        ),
                        (
                            f"<b>{t(code, 'start_title')}</b>"
                            f"\n\n"
                            f"{t(code, 'start_body')}"
                        ),
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                        reply_markup=markup,
                    )

            async def is_group_admin(
                self,
                chat_id: int,
                user_id: int,
            ) -> bool:

                try:

                    member = (
                        await self.api.get_chat_member(
                            chat_id,
                            user_id,
                        )
                    )

                    return (
                        member.get(
                            "status"
                        )
                        in {
                            "creator",
                            "administrator",
                        }
                    )

                except Exception:

                    return False

            async def bot_member(
                self,
                chat_id: int,
            ) -> Optional[
                dict[str, Any]
            ]:

                try:

                    return (
                        await self.api.get_chat_member(
                            chat_id,
                            self.bot_id,
                        )
                    )

                except Exception:

                    return None

            async def require_admin(
                self,
                message: dict[str, Any],
            ) -> tuple[
                Optional[dict[str, Any]],
                Optional[str],
            ]:

                chat = message.get(
                    "chat",
                    {},
                )

                user = message.get(
                    "from",
                    {},
                )

                chat_id = chat.get(
                    "id"
                )

                if chat.get(
                    "type"
                ) not in {
                    "group",
                    "supergroup",
                }:

                    lang = (
                        await self.db.get_user_language(
                            int(user["id"])
                        )
                    )

                    await self.api.send_message(
                        chat_id,
                        t(
                            lang,
                            "group_only",
                        ),
                    )

                    return (
                        None,
                        lang,
                    )

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

                group = (
                    await self.db.get_chat(
                        chat_id
                    )
                )

                lang = (
                    group["language"]
                    if group
                    else DEFAULT_LANGUAGE
                )

                if not await self.is_group_admin(
                    chat_id,
                    int(user["id"]),
                ):

                    await self.api.send_message(
                        chat_id,
                        t(
                            lang,
                            "admin_only",
                        ),
                    )

                    return (
                        None,
                        lang,
                    )

                return (
                    group,
                    lang,
                )

            async def handle_free(self,message:dict[str,Any],arg:str,remove:bool=False)->None:
                group,lang=await self.require_admin(message)
                if not group:return
                target=self._target_user(message,arg)
                chat_id=int(message["chat"]["id"])
                if not target:
                    await self.api.send_message(chat_id,t(lang,"free_usage")); return
                uid=int(target["id"])
                if remove:
                    actor=int(message.get("from",{}).get("id",0)); await self.db.remove_exempt_user(chat_id,uid); await self.db.audit("exempt_remove",chat_id,actor,details=f"user_id={uid}")
                    text=t(lang,"free_removed",mention=mention_html(target))
                else:
                    actor=int(message.get("from",{}).get("id",0)); await self.db.set_exempt_user(chat_id,uid,actor); await self.db.audit("exempt_add",chat_id,actor,details=f"user_id={uid}")
                    text=t(lang,"free_saved",mention=mention_html(target))
                await self.api.send_message(chat_id,text,parse_mode="HTML")

            async def handle_block_media(self,message:dict[str,Any],remove:bool=False)->None:
                group,lang=await self.require_admin(message)
                if not group:return
                reply=message.get("reply_to_message") or {}
                media=media_from_message(reply)
                chat_id=int(message["chat"]["id"])
                if not media:
                    await self.api.send_message(chat_id,t(lang,"blockmedia_usage")); return
                if remove:
                    actor=int(message.get("from",{}).get("id",0)); await self.db.unblock_media(chat_id,media.file_unique_id); await self.db.audit("media_unblock",chat_id,actor,details=f"key={media.file_unique_id}")
                    text=t(lang,"blockmedia_removed")
                else:
                    content_sha256=None
                    try:
                        data,_=await self.api.get_file_bytes(media.file_id)
                        content_sha256=hashlib.sha256(data).hexdigest()
                    except Exception as exc:
                        logging.debug("BLOCK_MEDIA_HASH_FAILED chat=%s key=%s error=%s",chat_id,media.file_unique_id[:16],exc)
                    actor=int(message.get("from",{}).get("id",0)); await self.db.block_media(chat_id,media.file_unique_id,media.kind,actor,content_sha256); await self.db.audit("media_block",chat_id,actor,details=f"key={media.file_unique_id} kind={media.kind}")
                    text=t(lang,"blockmedia_saved")
                await self.api.send_message(chat_id,text)

            async def handle_freelist(self,message:dict[str,Any])->None:
                group,lang=await self.require_admin(message)
                if not group:return
                cid=int(message["chat"]["id"]); items,total=await self.db.list_exempt_users(cid,0,50)
                lines=[]
                for r in items:
                    name=((r.get('first_name') or '')+' '+(r.get('last_name') or '')).strip() or f"User {r['user_id']}"
                    uname=(" @"+r['username']) if r.get('username') else ''
                    lines.append(f"• {esc(name)}{esc(uname)} · <code>{r['user_id']}</code>")
                await self.api.send_message(cid,(f"🆓 <b>Exempt users</b> · {total}\n\n"+('\n'.join(lines) if lines else '—')),parse_mode="HTML")

            async def handle_group_stats(self,message:dict[str,Any])->None:
                group,lang=await self.require_admin(message)
                if not group:return
                cid=int(message["chat"]["id"])
                st=await self.db.get_chat_stats(cid)
                await self.api.send_message(cid,t(lang,"group_detail_stats",**st,exempt=await self.db.exempt_count(cid),blocked=await self.db.blocked_count(cid)))

            async def handle_message(
                self,
                message: dict[str, Any],
            ) -> None:
                chat = message.get("chat") or {}
                user = message.get("from") or {}
                uid = int(user.get("id", 0))
                chat_id = int(chat.get("id", 0))
                chat_type = chat.get("type")

                logging.debug(
                    "UPDATE_MESSAGE chat=%s type=%s message_id=%s user=%s keys=%s",
                    chat_id,
                    chat_type,
                    message.get("message_id"),
                    uid,
                    sorted(message.keys()),
                )

                if user.get("is_bot"):
                    logging.debug(
                        "MESSAGE_SKIP reason=sender_is_bot chat=%s user=%s",
                        chat_id,
                        uid,
                    )
                    return

                if uid:
                    await self.db.upsert_user(
                        uid,
                        is_bot=bool(user.get("is_bot")),
                        username=user.get("username"),
                        first_name=user.get("first_name"),
                        last_name=user.get("last_name"),
                    )

                if chat_type in {"group", "supergroup"} and uid:
                    await self.db.track_chat_user(chat_id, user, message.get("message_id"))

                if await self.handle_owner_pending(message):
                    return

                if chat_type == "private" and uid != OWNER_ID and await self.db.is_user_blocked(uid):
                    logging.info("PRIVATE_MESSAGE_SKIPPED blocked_user=%s", uid)
                    return

                text = message.get("text") or ""
                cmd, arg = command_of(text)

                if cmd == "start":
                    await self.handle_start(message)
                    return
                if cmd == "help":
                    await self.handle_help(message)
                    return
                if cmd == "settings":
                    await self.handle_settings(message)
                    return
                if cmd == "setmessage":
                    await self.handle_setmessage(message, arg)
                    return
                if cmd == "stats":
                    await self.handle_stats(message)
                    return
                if cmd == "free":
                    await self.handle_free(message,arg,False); return
                if cmd == "unfree":
                    await self.handle_free(message,arg,True); return
                if cmd == "blockmedia":
                    await self.handle_block_media(message,False); return
                if cmd == "unblockmedia":
                    await self.handle_block_media(message,True); return
                if cmd == "freelist":
                    await self.handle_freelist(message); return
                if cmd == "groupstats":
                    await self.handle_group_stats(message); return
                if cmd == "owner":
                    await self.handle_owner_panel(message); return
                # Legacy owner commands remain supported for the owner, but are not listed publicly.
                if cmd == "ownerstats":
                    await self.handle_owner_stats(message); return
                if cmd == "groups":
                    await self.handle_owner_groups(message); return
                if cmd == "sendgroup":
                    await self.handle_owner_sendgroup(message,arg); return
                if cmd == "broadcastgroups":
                    await self.handle_owner_broadcast(message,arg,False); return
                if cmd == "broadcastusers":
                    await self.handle_owner_broadcast(message,arg,True); return
                if cmd == "test" and uid == OWNER_ID and chat_type == "private":
                    self.owner_pending[uid] = {"mode":"detection_test"}
                    lang = await self._owner_lang(uid)
                    await self.api.send_message(chat_id, self._owner_text(lang,"prompt_test"), reply_markup={"inline_keyboard":[[self._owner_button(self._owner_text(lang,"prompt_test_cancel"),"o:cancel")]]})
                    return

                if chat_type in {"group", "supergroup"}:
                    group = await self.db.ensure_chat(
                        chat_id,
                        chat.get("title", ""),
                        chat_type,
                    )
                else:
                    group = None

                media = media_from_message(message)
                if media:
                    logging.info(
                        "MEDIA_RECEIVED chat=%s user=%s message=%s kind=%s file_unique=%s size=%s",
                        chat_id,
                        uid,
                        message.get("message_id"),
                        media.kind,
                        media.file_unique_id[:16],
                        media.file_size,
                    )
                    await self.moderate(message, media, group)
                    return

                if (
                    chat_type == "private"
                    and text
                    and not text.startswith("/")
                ):
                    await self.api.send_message(
                        chat_id,
                        t(
                            await self.db.get_user_language(uid),
                            "unsupported_media",
                        ),
                    )

            async def handle_update(
                self,
                update: dict[str, Any],
            ) -> None:

                if "callback_query" in update:

                    callback = update[
                        "callback_query"
                    ]

                    data = callback.get(
                        "data",
                        "",
                    )

                    if data.startswith(
                        "lang:"
                    ):

                        await self.handle_language_callback(
                            callback,
                            data.split(
                                ":",
                                1,
                            )[1],
                        )

                    elif data == "start:language":

                        message = callback.get(
                            "message",
                            {},
                        )

                        await self.api.answer_callback(
                            callback["id"]
                        )

                        await self.language_picker(
                            int(
                                message[
                                    "chat"
                                ]["id"]
                            ),
                            int(
                                message[
                                    "message_id"
                                ]
                            ),
                        )

                    elif data.startswith("o:"):

                        await self.owner_callback(
                            callback
                        )

                    elif data.startswith("s:"):

                        await self.settings_callback(
                            callback
                        )

                    return

                if "message" in update:

                    await self.handle_message(
                        update[
                            "message"
                        ]
                    )

                    return

                if "my_chat_member" in update:

                    m = update[
                        "my_chat_member"
                    ]

                    chat = m.get(
                        "chat",
                        {},
                    )

                    if chat.get(
                        "type"
                    ) in {
                        "group",
                        "supergroup",
                    }:

                        await self.db.ensure_chat(
                            chat["id"],
                            chat.get(
                                "title",
                                "",
                            ),
                            chat.get(
                                "type",
                                "group",
                            ),
                        )
                        new_member = m.get("new_chat_member") or {}
                        status = new_member.get("status")
                        await self.db.mark_chat_membership(chat["id"], status not in {"left","kicked"})
