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

class ModerationMixin:
            def _memory_get(
                self,
                key: str,
            ) -> Optional[float]:

                item = self.memory_cache.get(
                    key
                )

                if item is None:
                    return None

                confidence, signature = item

                if (
                    signature
                    != self.detector.signature
                ):

                    self.memory_cache.pop(
                        key,
                        None,
                    )

                    return None

                self.memory_cache.move_to_end(
                    key
                )

                return confidence

            def _memory_put(
                self,
                key: str,
                confidence: float,
            ) -> None:

                self.memory_cache[
                    key
                ] = (
                    float(confidence),
                    self.detector.signature,
                )

                self.memory_cache.move_to_end(
                    key
                )

                while (
                    len(self.memory_cache)
                    > self.memory_cache_limit
                ):

                    self.memory_cache.popitem(
                        last=False
                    )

            def _augment_image_views(image: Image.Image) -> list[Image.Image]:
                base = _resize_frame(image)
                if not IMAGE_TTA:
                    return [base]
                views = [base]
                try:
                    w,h=base.size
                    side=min(w,h)
                    left=max(0,(w-side)//2); top=max(0,(h-side)//2)
                    crop=base.crop((left,top,left+side,top+side))
                    views.append(crop)
                    views.append(base.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
                    # Mild vertical-safe crop for tall/wide images.
                    if w != h:
                        if w > h:
                            crop2=base.crop((0, max(0,(h-side)//2), w, max(0,(h-side)//2)+side))
                        else:
                            crop2=base.crop((max(0,(w-side)//2),0,max(0,(w-side)//2)+side,h))
                        views.append(crop2)
                except Exception:
                    pass
                unique=[]; seen=set()
                for v in views:
                    thumb=v.copy(); thumb.thumbnail((40,40),Image.Resampling.BILINEAR); fp=hashlib.sha1(thumb.tobytes()).hexdigest()
                    if fp not in seen:
                        seen.add(fp); unique.append(v)
                return unique[:4]

            def _aggregate_frame_scores(scores: list[float]) -> float:
                if not scores:
                    return 0.0
                ordered=sorted((float(x) for x in scores), reverse=True)
                top=ordered[0]
                k=max(1, int(round(len(ordered)*FRAME_TOPK_PERCENT)))
                topk=sum(ordered[:k])/k
                # Preserve the strongest frame, then reward consistent support across views/frames.
                support=max(0.0, topk-0.50)
                return float(min(1.0, top + support*0.20))

            async def _detect_media_once(
                self,
                media: MediaRef,
            ) -> float:
                started = time.perf_counter()
                cache_key = media.file_unique_id

                memory_hit = self._memory_get(cache_key)
                if memory_hit is not None:
                    logging.info(
                        "CACHE_HIT layer=memory kind=%s unique=%s confidence=%.4f",
                        media.kind,
                        cache_key[:16],
                        memory_hit,
                    )
                    return memory_hit

                async with self.inflight_lock:
                    memory_hit = self._memory_get(cache_key)
                    if memory_hit is not None:
                        logging.info(
                            "CACHE_HIT layer=memory-after-lock kind=%s unique=%s confidence=%.4f",
                            media.kind,
                            cache_key[:16],
                            memory_hit,
                        )
                        return memory_hit

                    existing = self.inflight.get(cache_key)
                    if existing is None:
                        future = asyncio.get_running_loop().create_future()
                        self.inflight[cache_key] = future
                        leader = True
                    else:
                        future = existing
                        leader = False

                if not leader:
                    confidence = await future
                    logging.info(
                        "INFLIGHT_JOIN kind=%s unique=%s confidence=%.4f",
                        media.kind,
                        cache_key[:16],
                        confidence,
                    )
                    return confidence

                try:
                    cached = await self.db.get_cached_detection(
                        cache_key,
                        self.detector.signature,
                    )
                    if cached:
                        confidence = float(cached["confidence"])
                        self._memory_put(cache_key, confidence)
                        future.set_result(confidence)
                        logging.info(
                            "CACHE_HIT layer=mysql kind=%s unique=%s confidence=%.4f elapsed_ms=%.1f",
                            media.kind,
                            cache_key[:16],
                            confidence,
                            (time.perf_counter() - started) * 1000,
                        )
                        return confidence

                    data, meta = await self.api.get_file_bytes(media.file_id)
                    sha256 = hashlib.sha256(data).hexdigest()
                    path = str(meta.get("file_path") or "")

                    logging.info(
                        "MEDIA_FETCH kind=%s unique=%s size=%d sha256=%s path=%s",
                        media.kind,
                        cache_key[:16],
                        len(data),
                        sha256[:16],
                        path,
                    )

                    cached = await self.db.get_cached_detection(
                        cache_key,
                        self.detector.signature,
                        sha256,
                    )
                    if cached:
                        confidence = float(cached["confidence"])
                        self._memory_put(cache_key, confidence)
                        future.set_result(confidence)
                        logging.info(
                            "CACHE_HIT layer=mysql-content kind=%s unique=%s confidence=%.4f",
                            media.kind,
                            cache_key[:16],
                            confidence,
                        )
                        return confidence

                    async with self.sem:
                        frames, duration = await extract_media_frames(
                            data,
                            media.kind,
                            VIDEO_MAX_FRAMES if media.kind == "video" else (
                                GIF_MAX_FRAMES if media.kind == "gif" else (
                                    TGS_MAX_FRAMES if media.kind == "tgs" else 1
                                )
                            ),
                        )

                        if not frames:
                            raise ValueError(
                                f"No decodable frames for media kind={media.kind}"
                            )

                        if media.kind == "image" and IMAGE_TTA:
                            expanded=[]
                            for frame in frames[:1]:
                                expanded.extend(self._augment_image_views(frame))
                            frames=expanded

                        logging.info(
                            "MEDIA_DECODE kind=%s unique=%s frames=%d duration=%s",
                            media.kind,
                            cache_key[:16],
                            len(frames),
                            f"{duration:.3f}s" if duration is not None else "unknown",
                        )

                        best_confidence = 0.0
                        best_index = -1
                        frame_scores: list[float] = []

                        for batch_start in range(0, len(frames), INFERENCE_BATCH_SIZE):
                            batch = frames[batch_start:batch_start + INFERENCE_BATCH_SIZE]
                            results = await asyncio.to_thread(
                                self.detector.predict_batch,
                                batch,
                            )

                            for offset, (_, score) in enumerate(results):
                                score = float(score)
                                frame_scores.append(score)
                                frame_index = batch_start + offset
                                if score > best_confidence:
                                    best_confidence = score
                                    best_index = frame_index

                            logging.debug(
                                "MODEL_BATCH kind=%s unique=%s start=%d count=%d scores=%s",
                                media.kind,
                                cache_key[:16],
                                batch_start,
                                len(batch),
                                [round(score, 4) for score in frame_scores[-len(batch):]],
                            )

                        confidence = self._aggregate_frame_scores(frame_scores)
                        if frame_scores:
                            best_index = max(range(len(frame_scores)), key=lambda i: frame_scores[i])

                    await self.db.save_detection(
                        cache_key,
                        sha256,
                        confidence >= 0.5,
                        confidence,
                        media.kind,
                        self.detector.signature,
                    )

                    self._memory_put(cache_key, confidence)
                    future.set_result(confidence)

                    top_scores = sorted(
                        enumerate(frame_scores),
                        key=lambda item: item[1],
                        reverse=True,
                    )[:5]

                    logging.info(
                        "MODEL_RESULT kind=%s unique=%s frames=%d best_frame=%d confidence=%.4f top=%s elapsed_ms=%.1f",
                        media.kind,
                        cache_key[:16],
                        len(frame_scores),
                        best_index,
                        confidence,
                        [(idx, round(score, 4)) for idx, score in top_scores],
                        (time.perf_counter() - started) * 1000,
                    )
                    return confidence

                except Exception as exc:
                    logging.exception(
                        "MEDIA_ERROR kind=%s unique=%s error=%s",
                        media.kind,
                        cache_key[:16],
                        exc,
                    )
                    if not future.done():
                        future.set_exception(exc)
                    raise

                finally:
                    async with self.inflight_lock:
                        self.inflight.pop(cache_key, None)

            async def moderate(
                self,
                message: dict[str, Any],
                media: MediaRef,
                group: Optional[dict[str, Any]],
            ) -> None:
                chat = message.get("chat", {})
                chat_id = int(chat.get("id", 0))
                user = message.get("from") or {}
                uid = int(user.get("id", 0))

                if chat.get("type") in {"group", "supergroup"}:
                    if not group or not group["enabled"]:
                        logging.debug(
                            "MODERATION_SKIP reason=disabled chat=%s kind=%s",
                            chat_id,
                            media.kind,
                        )
                        return
                    lang = group["language"]
                    if uid and await self.db.is_exempt_user(chat_id,uid):
                        logging.info("MODERATION_SKIP reason=exempt chat=%s user=%s",chat_id,uid); return
                    if uid and not group.get("moderate_admins"):
                        try:
                            member=await self.api.get_chat_member(chat_id,uid)
                            if member and member.get("status") in {"creator","administrator"}:
                                logging.info("MODERATION_SKIP reason=admin_setting_off chat=%s user=%s",chat_id,uid); return
                        except Exception: pass
                else:
                    lang = await self.db.get_user_language(uid)

                if chat.get("type") in {"group","supergroup"} and await self.db.is_media_blocked(chat_id,media.file_unique_id):
                    logging.info("MEDIA_BLOCKED chat=%s user=%s kind=%s",chat_id,uid,media.kind)
                    try: await self.api.delete_message(chat_id,int(message["message_id"]))
                    except Exception as exc: logging.warning("BLOCKED_MEDIA_DELETE_FAILED chat=%s error=%s",chat_id,exc)
                    await self.db.record_chat_action(chat_id,deleted=True)
                    await self.api.send_message(chat_id,t(lang,"media_blocked")); return

                if media.file_size and media.file_size > MAX_MEDIA_BYTES:
                    logging.warning(
                        "MODERATION_SKIP reason=file_too_large chat=%s kind=%s size=%s limit=%s",
                        chat_id,
                        media.kind,
                        media.file_size,
                        MAX_MEDIA_BYTES,
                    )
                    await self.api.send_message(
                        chat_id,
                        t(lang, "media_too_large"),
                    )
                    return

                try:
                    confidence = await self._detect_media_once(media)
                except ValueError as exc:
                    logging.warning(
                        "MODERATION_DECODE_FAILED chat=%s kind=%s error=%s",
                        chat_id,
                        media.kind,
                        exc,
                    )
                    if chat.get("type") == "private":
                        await self.api.send_message(
                            chat_id,
                            t(lang, "media_too_large"),
                        )
                    return
                except (UnidentifiedImageError, OSError, RuntimeError) as exc:
                    logging.warning(
                        "MODERATION_MEDIA_FAILED chat=%s kind=%s error=%s",
                        chat_id,
                        media.kind,
                        exc,
                    )
                    return
                except Exception as exc:
                    logging.exception(
                        "MODERATION_UNEXPECTED_FAILURE chat=%s kind=%s error=%s",
                        chat_id,
                        media.kind,
                        exc,
                    )
                    return

                if chat.get("type") in {"group","supergroup"}:
                    detected_hash=await self.db.get_detection_hash(media.file_unique_id)
                    if await self.db.is_media_blocked(chat_id,media.file_unique_id,detected_hash):
                        logging.info("MEDIA_BLOCKED content-match chat=%s user=%s kind=%s",chat_id,uid,media.kind)
                        try: await self.api.delete_message(chat_id,int(message["message_id"]))
                        except Exception as exc: logging.warning("BLOCKED_MEDIA_DELETE_FAILED chat=%s error=%s",chat_id,exc)
                        await self.db.record_chat_action(chat_id,deleted=True)
                        await self.api.send_message(chat_id,t(lang,"media_blocked")); return

                try:
                    threshold = (
                        float(group["threshold"])
                        if group is not None
                        else DEFAULT_THRESHOLD
                    )
                except (TypeError, ValueError, KeyError):
                    threshold = DEFAULT_THRESHOLD

                threshold = min(1.0, max(0.0, threshold))
                is_nsfw = confidence >= threshold

                if chat.get("type") in {"group","supergroup"}:
                    await self.db.record_chat_check(chat_id,is_nsfw)

                logging.info(
                    "DECISION chat=%s user=%s kind=%s confidence=%.4f threshold=%.4f decision=%s action=%s",
                    chat_id,
                    uid,
                    media.kind,
                    confidence,
                    threshold,
                    "NSFW" if is_nsfw else "SAFE",
                    group.get("action") if group else "private-report",
                )

                if not is_nsfw:
                    if chat.get("type") == "private":
                        await self.api.send_message(
                            chat_id,
                            t(
                                lang,
                                "private_safe",
                                confidence=confidence,
                            ),
                        )
                    return

                if chat.get("type") == "private":
                    await self.api.send_message(
                        chat_id,
                        t(
                            lang,
                            "private_nsfw",
                            confidence=confidence,
                        ),
                    )
                    return

                await self.apply_group_action(
                    message,
                    group,
                    confidence,
                )

            async def apply_group_action(
                self,
                message: dict[str, Any],
                group: dict[str, Any],
                confidence: float,
            ) -> None:
                chat_id = int(message["chat"]["id"])
                user = message.get("from") or {}
                uid = int(user.get("id", 0))
                lang = group["language"]
                configured_action = group["action"]
                effective_action = configured_action
                mention = mention_html(user)

                logging.info(
                    "ACTION_START chat=%s user=%s confidence=%.4f configured=%s",
                    chat_id,
                    uid,
                    confidence,
                    configured_action,
                )

                delete_ok = False
                try:
                    await self.api.delete_message(
                        chat_id,
                        int(message["message_id"]),
                    )
                    delete_ok = True
                    await self.db.record_chat_action(chat_id,deleted=True)
                except Exception as exc:
                    logging.warning(
                        "ACTION_DELETE_FAILED chat=%s user=%s error=%s",
                        chat_id,
                        uid,
                        exc,
                    )

                warning_count: int | None = None
                action_ok = True

                if configured_action == "warn":
                    warning_count = await self.db.add_warning(chat_id, uid)
                    logging.info(
                        "WARNING_COUNT chat=%s user=%s count=%s limit=%s",
                        chat_id,
                        uid,
                        warning_count,
                        group["warn_limit"],
                    )

                    if (
                        warning_count >= int(group["warn_limit"])
                        and group["escalation"] != "none"
                    ):
                        effective_action = group["escalation"]
                        await self.db.reset_warnings(chat_id, uid)
                        logging.info(
                            "ESCALATE chat=%s user=%s action=%s",
                            chat_id,
                            uid,
                            effective_action,
                        )
                    else:
                        effective_action = "warn"

                try:
                    if effective_action == "mute":
                        until = int(time.time()) + max(
                            60,
                            int(group["mute_minutes"]) * 60,
                        )
                        await self.api.restrict_member(
                            chat_id,
                            uid,
                            until,
                        )
                    elif effective_action == "kick":
                        await self.api.ban_member(chat_id, uid)
                        await asyncio.sleep(0.5)
                        await self.api.unban_member(chat_id, uid)
                    elif effective_action == "ban":
                        await self.api.ban_member(chat_id, uid)
                    elif effective_action == "warn":
                        pass
                    else:
                        raise RuntimeError(
                            f"unknown effective action: {effective_action}"
                        )
                except Exception as exc:
                    action_ok = False
                    logging.exception(
                        "ACTION_FAILED chat=%s user=%s action=%s error=%s",
                        chat_id,
                        uid,
                        effective_action,
                        exc,
                    )

                if effective_action == "warn":
                    success = action_ok and delete_ok
                else:
                    success = action_ok and delete_ok

                logging.info(
                    "ACTION_RESULT chat=%s user=%s configured=%s effective=%s delete_ok=%s action_ok=%s success=%s warnings=%s",
                    chat_id,
                    uid,
                    configured_action,
                    effective_action,
                    delete_ok,
                    action_ok,
                    success,
                    warning_count,
                )

                custom = group.get("custom_message")
                if custom:
                    response = custom.replace("{mention}", mention)
                    response = response.replace("{confidence}", f"{confidence:.1%}")
                    response = response.replace(
                        "{action}",
                        t(lang, f"action_{effective_action}"),
                    )
                else:
                    response = t(
                        lang,
                        "group_detected",
                        mention=mention,
                    )

                if not success:
                    response += "\n\n" + t(lang, "action_failed")

                try:
                    await self.api.send_message(
                        chat_id,
                        response,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception as exc:
                    logging.warning(
                        "MODERATION_RESPONSE_FAILED chat=%s error=%s",
                        chat_id,
                        exc,
                    )
