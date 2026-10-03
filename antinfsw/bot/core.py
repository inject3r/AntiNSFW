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

class BotCore:
            def __init__(
                self,
                api: TelegramAPI,
                db: Database,
                detector: ModelDetector,
            ):

                self.api = api
                self.db = db
                self.detector = detector

                self.offset = 0

                self.bot_id = 0
                self.bot_username = ""

                self.started_at = (
                    time.monotonic()
                )

                self.sem = asyncio.Semaphore(
                    1
                )

                self.tasks: set[
                    asyncio.Task[Any]
                ] = set()

                self.memory_cache: OrderedDict[
                    str,
                    tuple[float, str],
                ] = OrderedDict()

                self.memory_cache_limit = 5000

                self.inflight: dict[
                    str,
                    asyncio.Future[float],
                ] = {}

                self.inflight_lock = asyncio.Lock()

                self.shutdown_event = (
                    asyncio.Event()
                )

                # Owner-only conversational actions started from inline buttons.
                self.owner_pending: dict[int, dict[str, Any]] = {}

            async def initialize(self) -> None:

                me = await self.api.call(
                    "getMe"
                )

                self.bot_id = me[
                    "id"
                ]

                self.bot_username = me.get(
                    "username",
                    "",
                )

                await self.api.call(
                    "deleteWebhook",
                    {
                        "drop_pending_updates": False,
                    },
                )

                await self.api.set_my_commands()

                logging.info(
                    "Bot started as @%s (%s)",
                    self.bot_username,
                    self.bot_id,
                )

            async def run(self) -> None:
                try:

                    while (
                        not self.shutdown_event.is_set()
                    ):

                        try:

                            updates = (
                                await self.api.get_updates(
                                    self.offset
                                )
                            )

                        except Exception as exc:

                            logging.warning(
                                "Polling error: %s",
                                exc,
                            )

                            await asyncio.sleep(
                                3
                            )

                            continue

                        for update in updates:

                            self.offset = max(
                                self.offset,
                                int(
                                    update[
                                        "update_id"
                                    ]
                                ) + 1,
                            )

                            logging.debug(
                                "UPDATE_RECEIVED update_id=%s keys=%s",
                                update.get("update_id"),
                                sorted(update.keys()),
                            )

                            task = asyncio.create_task(
                                self.handle_update(update)
                            )

                            self.tasks.add(task)

                            def _task_done(done: asyncio.Task[Any]) -> None:
                                self.tasks.discard(done)
                                try:
                                    error = done.exception()
                                except asyncio.CancelledError:
                                    return
                                if error is not None:
                                    logging.error(
                                        "UPDATE_TASK_FAILED error=%r",
                                        error,
                                        exc_info=(type(error), error, error.__traceback__),
                                    )

                            task.add_done_callback(_task_done)

                        await asyncio.sleep(
                            0
                        )

                finally:

                    for task in list(self.tasks):

                        task.cancel()

                    await asyncio.gather(
                        *self.tasks,
                        return_exceptions=True,
                    )
