from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import tempfile
from typing import Any, Optional

import numpy as np
import torch
from PIL import Image, ImageSequence, UnidentifiedImageError
from transformers import AutoImageProcessor, AutoModelForImageClassification

try:
    import av
except ImportError:
    av = None

try:
    from rlottie_python import LottieAnimation
except ImportError:
    LottieAnimation = None

from .common import MediaRef
from .config import (
    DETECTOR_CACHE_VERSION, FRAME_MAX_SIDE, FRAME_TOPK_PERCENT, GIF_MAX_FRAMES,
    IMAGE_TTA, INFERENCE_BATCH_SIZE, INFERENCE_BATCH_WAIT_MS, MAX_MEDIA_BYTES,
    MAX_VIDEO_DURATION_SECONDS, MODEL_ID, TGS_MAX_FRAMES, VIDEO_MAX_FRAMES,
)

class ModelDetector:

    def __init__(
        self,
        model_id: str,
    ):

        logging.info(
            "Loading model: %s",
            model_id,
        )

        cpu_count = max(
            1,
            min(
                4,
                os.cpu_count() or 4,
            ),
        )

        torch.set_num_threads(
            cpu_count
        )

        try:

            torch.set_num_interop_threads(
                max(
                    1,
                    min(
                        2,
                        cpu_count,
                    ),
                )
            )

        except RuntimeError:
            pass

        self.device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        self.processor = (
            AutoImageProcessor.from_pretrained(
                model_id
            )
        )

        self.model = (
            AutoModelForImageClassification
            .from_pretrained(
                model_id
            )
        )

        self.model.to(
            self.device
        )

        self.model.eval()

        self.model_id = model_id

        self.signature = hashlib.sha256(
            (
                f"{model_id}|"
                f"{DETECTOR_CACHE_VERSION}|"
                f"{INFERENCE_BATCH_SIZE}|"
                f"{VIDEO_MAX_FRAMES}|{GIF_MAX_FRAMES}|{TGS_MAX_FRAMES}|{MAX_VIDEO_DURATION_SECONDS}|{FRAME_MAX_SIDE}"
            ).encode()
        ).hexdigest()[:24]

        id2label = (
            getattr(
                self.model.config,
                "id2label",
                {},
            )
            or {}
        )

        self.nsfw_index = next(
            (
                int(idx)
                for idx, label
                in id2label.items()
                if str(label).lower()
                == "nsfw"
            ),
            1,
        )

        labels = {str(k): str(v) for k, v in id2label.items()}
        logging.info(
            "MODEL_READY device=%s signature=%s nsfw_index=%s labels=%s",
            self.device,
            self.signature,
            self.nsfw_index,
            labels,
        )

    def predict_batch(
        self,
        images: list[Image.Image],
    ) -> list[tuple[bool, float]]:

        if not images:
            return []

        normalized = [
            img.convert("RGB")
            if img.mode != "RGB"
            else img
            for img in images
        ]

        inputs = self.processor(
            images=normalized,
            return_tensors="pt",
        )

        inputs = {
            key: value.to(
                self.device
            )
            for key, value in inputs.items()
        }

        with torch.inference_mode():

            logits = self.model(
                **inputs
            ).logits

            probs = torch.softmax(
                logits,
                dim=-1,
            )[
                :,
                self.nsfw_index,
            ]

        return [
            (
                bool(
                    probability.item()
                    >= 0.5
                ),
                float(
                    probability.item()
                ),
            )
            for probability in probs
        ]

    def predict(
        self,
        image: Image.Image,
    ) -> tuple[bool, float]:

        return self.predict_batch(
            [image]
        )[0]

def command_of(
    text: str,
) -> tuple[str, str]:

    text = (
        text or ""
    ).strip()

    if not text.startswith("/"):
        return "", ""

    parts = text.split(
        None,
        1,
    )

    cmd = parts[0][1:]

    cmd = cmd.split(
        "@",
        1,
    )[0].lower()

    arg = (
        parts[1].strip()
        if len(parts) > 1
        else ""
    )

    return (
        cmd,
        arg,
    )

def mention_html(
    user: dict[str, Any],
) -> str:

    uid = user.get(
        "id"
    )

    name = (
        user.get(
            "first_name"
        )
        or "User"
    )

    return (
        f'<a href="tg://user?id={uid}">'
        f"{esc(name)}"
        f"</a>"
    )

def _file_name(item: dict[str, Any]) -> str:
    return str(item.get("file_name") or "").lower()

def _mime_type(item: dict[str, Any]) -> str:
    return str(item.get("mime_type") or "").lower()

def _sample_indices(total: int, maximum: int) -> list[int]:
    if total <= 0 or maximum <= 0:
        return []
    if total <= maximum:
        return list(range(total))
    if maximum == 1:
        return [0]
    return sorted({
        int(round(i * (total - 1) / (maximum - 1)))
        for i in range(maximum)
    })

def media_from_message(
    message: dict[str, Any],
) -> Optional[MediaRef]:
    """Map Telegram media objects to a decoder kind.

    Kinds:
      image      - single-frame images / WEBP stickers
      gif        - GIF or other animated raster images
      tgs        - Telegram animated sticker (gzip/Lottie)
      video      - MP4/WebM/video-note/animation media
    """

    if message.get("photo"):
        item = message["photo"][-1]
        return MediaRef(
            item["file_id"],
            item["file_unique_id"],
            "image",
            item.get("file_size"),
        )

    if message.get("video"):
        item = message["video"]
        return MediaRef(
            item["file_id"],
            item["file_unique_id"],
            "video",
            item.get("file_size"),
        )

    if message.get("video_note"):
        item = message["video_note"]
        return MediaRef(
            item["file_id"],
            item["file_unique_id"],
            "video",
            item.get("file_size"),
        )

    if message.get("animation"):
        item = message["animation"]
        mime = _mime_type(item)
        name = _file_name(item)
        kind = "gif" if mime == "image/gif" or name.endswith(".gif") else "video"
        return MediaRef(
            item["file_id"],
            item["file_unique_id"],
            kind,
            item.get("file_size"),
        )

    if message.get("sticker"):
        item = message["sticker"]
        if item.get("is_animated"):
            return MediaRef(
                item["file_id"],
                item["file_unique_id"],
                "tgs",
                item.get("file_size"),
            )
        if item.get("is_video"):
            return MediaRef(
                item["file_id"],
                item["file_unique_id"],
                "video",
                item.get("file_size"),
            )
        return MediaRef(
            item["file_id"],
            item["file_unique_id"],
            "image",
            item.get("file_size"),
        )

    if message.get("document"):
        item = message["document"]
        mime = _mime_type(item)
        name = _file_name(item)

        if (
            mime == "application/x-tgsticker"
            or name.endswith(".tgs")
        ):
            kind = "tgs"
        elif mime == "image/gif" or name.endswith(".gif"):
            kind = "gif"
        elif mime.startswith("video/") or name.endswith((".mp4", ".webm", ".mov", ".mkv", ".avi")):
            kind = "video"
        elif mime.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")):
            kind = "image"
        else:
            return None

        return MediaRef(
            item["file_id"],
            item["file_unique_id"],
            kind,
            item.get("file_size"),
        )

    return None

def _resize_frame(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    width, height = image.size
    if max(width, height) > FRAME_MAX_SIDE:
        image.thumbnail((FRAME_MAX_SIDE, FRAME_MAX_SIDE), Image.Resampling.LANCZOS)
    return image.copy()

def _decode_raster_frames_sync(
    data: bytes,
    maximum: int,
) -> tuple[list[Image.Image], float | None]:
    frames: list[Image.Image] = []
    duration: float | None = None

    with Image.open(io.BytesIO(data)) as image:
        total = int(getattr(image, "n_frames", 1) or 1)

        frame_durations_ms: list[float] = []
        if total > 1:
            try:
                for idx in range(total):
                    image.seek(idx)
                    frame_durations_ms.append(float(image.info.get("duration", 0) or 0))
                if frame_durations_ms:
                    duration = sum(frame_durations_ms) / 1000.0
            except Exception:
                duration = None

        indices = _sample_indices(total, maximum)
        for idx in indices:
            try:
                image.seek(idx)
                frames.append(_resize_frame(image))
            except (EOFError, UnidentifiedImageError, OSError):
                continue

    return frames, duration

def _decode_video_frames_sync(
    data: bytes,
    maximum: int,
) -> tuple[list[Image.Image], float | None]:
    if av is None:
        raise RuntimeError(
            "PyAV is not installed; install dependency 'av' to decode video/WebM/MP4 media"
        )

    frames: list[Image.Image] = []
    duration: float | None = None

    with av.open(io.BytesIO(data), mode="r") as container:
        video_stream = next(
            (stream for stream in container.streams if stream.type == "video"),
            None,
        )
        if video_stream is None:
            raise RuntimeError("No video stream found")

        try:
            if video_stream.duration is not None and video_stream.time_base is not None:
                duration = float(video_stream.duration * video_stream.time_base)
        except Exception:
            duration = None

        if duration is not None and duration > MAX_VIDEO_DURATION_SECONDS:
            duration = MAX_VIDEO_DURATION_SECONDS

        # Prefer evenly-spaced seeks across the whole clip. This catches
        # short NSFW segments much more reliably than a fixed FPS.
        if duration and duration > 0:
            targets = [
                duration * i / max(1, maximum - 1)
                for i in range(maximum)
            ]
            for target in targets:
                try:
                    time_base = float(video_stream.time_base)
                    pts = int(target / time_base)
                    container.seek(
                        pts,
                        stream=video_stream,
                        any_frame=False,
                        backward=True,
                    )
                    chosen = None
                    chosen_time = -1.0
                    for frame in container.decode(video_stream):
                        frame_time = float(frame.time) if frame.time is not None else chosen_time
                        chosen = frame
                        chosen_time = frame_time
                        if frame_time >= target:
                            break
                    if chosen is not None:
                        frames.append(_resize_frame(chosen.to_image()))
                except Exception:
                    continue

        # Fallback for containers with missing/unreliable duration metadata.
        if not frames:
            container.seek(0)
            decoded: list[Image.Image] = []
            for frame in container.decode(video_stream):
                decoded.append(_resize_frame(frame.to_image()))
                if len(decoded) >= maximum * 4:
                    break
            if decoded:
                frames = [decoded[i] for i in _sample_indices(len(decoded), maximum)]

    # Remove accidental duplicate frames produced by seek/decoder rounding.
    unique: list[Image.Image] = []
    fingerprints: set[str] = set()
    for frame in frames:
        thumb = frame.copy()
        thumb.thumbnail((32, 32), Image.Resampling.BILINEAR)
        fp = hashlib.sha1(thumb.tobytes()).hexdigest()
        if fp not in fingerprints:
            fingerprints.add(fp)
            unique.append(frame)

    return unique[:maximum], duration

def _decode_tgs_frames_sync(
    data: bytes,
    maximum: int,
) -> tuple[list[Image.Image], float | None]:
    if LottieAnimation is None:
        raise RuntimeError(
            "rlottie-python is not installed; install dependency 'rlottie-python[full]' to decode TGS stickers"
        )

    frames: list[Image.Image] = []
    duration: float | None = None

    with tempfile.NamedTemporaryFile(prefix="nsfw_guard_", suffix=".tgs") as handle:
        handle.write(data)
        handle.flush()

        anim = LottieAnimation.from_tgs(handle.name)
        try:
            total = max(1, int(anim.lottie_animation_get_totalframe()))
            fps = float(anim.lottie_animation_get_framerate() or 0)
            if fps > 0 and total > 0:
                duration = total / fps

            for index in _sample_indices(total, maximum):
                try:
                    frame = anim.render_pillow_frame(frame_num=index)
                    if frame is not None:
                        frames.append(_resize_frame(frame))
                except Exception as exc:
                    logging.debug(
                        "TGS_FRAME_RENDER_FAIL index=%s error=%s",
                        index,
                        exc,
                    )
        finally:
            try:
                close = getattr(anim, "close", None)
                if callable(close):
                    close()
            except Exception:
                pass

    return frames, duration

async def extract_media_frames(
    data: bytes,
    kind: str,
    maximum: int,
) -> tuple[list[Image.Image], float | None]:
    """Decode an arbitrary Telegram media payload into sampled RGB frames."""
    if kind in {"image", "gif"}:
        return await asyncio.to_thread(
            _decode_raster_frames_sync,
            data,
            maximum if kind == "gif" else 1,
        )

    if kind == "tgs":
        return await asyncio.to_thread(
            _decode_tgs_frames_sync,
            data,
            maximum,
        )

    return await asyncio.to_thread(
        _decode_video_frames_sync,
        data,
        maximum,
    )
