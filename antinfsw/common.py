from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any, Optional

from .config import TRANSLATIONS

def t(lang: str, key: str, **kwargs: Any) -> str:
    lang = lang if lang in TRANSLATIONS else "en"
    value = TRANSLATIONS[lang].get(key, TRANSLATIONS["en"].get(key, key))
    try:
        return value.format(**kwargs)
    except (KeyError, ValueError):
        return value

def esc(value: Any) -> str:
    return html.escape(str(value), quote=False)

@dataclass
class MediaRef:
    file_id: str
    file_unique_id: str
    kind: str
    file_size: Optional[int] = None
