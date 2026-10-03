from __future__ import annotations

import asyncio
import logging

from .bot import Bot
from .config import (
    DEFAULT_LANGUAGE, DEFAULT_THRESHOLD, GIF_MAX_FRAMES, LANGUAGES,
    LOG_LEVEL, MAX_MEDIA_BYTES, MODEL_ID, TGS_MAX_FRAMES, VIDEO_MAX_FRAMES,
)
from .database import Database
from .detector import LottieAnimation, ModelDetector, av
from .telegram import TelegramAPI

async def main() -> None:
    if DEFAULT_LANGUAGE not in LANGUAGES:
        raise SystemExit("DEFAULT_LANGUAGE must be one of: " + ", ".join(LANGUAGES))

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(process)d | %(name)s | %(message)s",
    )

    logging.info(
        "Starting NSFW Guard | model=%s threshold=%.2f video_frames=%d gif_frames=%d tgs_frames=%d max_media_mb=%.1f av=%s rlottie=%s",
        MODEL_ID, DEFAULT_THRESHOLD, VIDEO_MAX_FRAMES, GIF_MAX_FRAMES,
        TGS_MAX_FRAMES, MAX_MEDIA_BYTES / (1024 * 1024), bool(av), bool(LottieAnimation),
    )

    db = Database()
    api = TelegramAPI()
    try:
        detector = ModelDetector(MODEL_ID)
        bot = Bot(api, db, detector)
        await bot.initialize()
        await bot.run()
    finally:
        db.close()
        await api.close()

if __name__ == "__main__":
    asyncio.run(main())
