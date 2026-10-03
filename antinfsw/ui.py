from __future__ import annotations

from typing import Any

from .common import t
from .config import LANGUAGES

def settings_keyboard(
    chat: dict[str, Any],
    lang: str,
) -> dict[str, Any]:

    state = (
        "ON"
        if chat["enabled"]
        else "OFF"
    )

    if lang == "fa":

        state = (
            "فعال"
            if chat["enabled"]
            else "غیرفعال"
        )

    elif lang == "ar":

        state = (
            "مفعلة"
            if chat["enabled"]
            else "معطلة"
        )

    elif lang == "ru":

        state = (
            "вкл."
            if chat["enabled"]
            else "выкл."
        )

    elif lang == "de":

        state = (
            "AN"
            if chat["enabled"]
            else "AUS"
        )

    elif lang == "fr":

        state = (
            "ON"
            if chat["enabled"]
            else "OFF"
        )

    elif lang == "zh":

        state = (
            "开"
            if chat["enabled"]
            else "关"
        )

    elif lang == "ja":

        state = (
            "オン"
            if chat["enabled"]
            else "オフ"
        )

    return {
        "inline_keyboard": [
            [
                {
                    "text": t(
                        lang,
                        "btn_toggle",
                        state=state,
                    ),
                    "callback_data": "s:toggle",
                }
            ],
            [
                {
                    "text": t(
                        lang,
                        "btn_language",
                    ),
                    "callback_data": "s:lang",
                },
                {
                    "text": t(
                        lang,
                        "btn_threshold",
                    ),
                    "callback_data": "s:threshold",
                },
            ],
            [
                {
                    "text": t(
                        lang,
                        "btn_action",
                    ),
                    "callback_data": "s:action",
                },
                {
                    "text": t(
                        lang,
                        "btn_warn",
                    ),
                    "callback_data": "s:warn",
                },
            ],
            [
                {
                    "text": t(
                        lang,
                        "btn_escalation",
                    ),
                    "callback_data": "s:esc",
                },
                {
                    "text": t(
                        lang,
                        "btn_mute",
                    ),
                    "callback_data": "s:mute",
                },
            ],
            [
                {
                    "text": t(
                        lang,
                        "btn_message",
                    ),
                    "callback_data": "s:message",
                }
            ],
            [
                {
                    "text": t(
                        lang,
                        "btn_reset_message",
                    ),
                    "callback_data": "s:reset",
                }
            ],
            [
                {
                    "text": t(lang, "btn_admin_moderation", state=(t(lang,"admin_mod_on") if chat.get("moderate_admins") else t(lang,"admin_mod_off"))),
                    "callback_data": "s:admins",
                }
            ],
        ]
    }

def settings_text(
    chat: dict[str, Any],
    lang: str,
) -> str:

    return (
        f"<b>{t(lang, 'settings_title')}</b>\n\n"
        +
        t(
            lang,
            "settings_summary",
            enabled=(
                "ON"
                if chat["enabled"]
                else "OFF"
            ),
            language=LANGUAGES.get(
                chat["language"],
                LANGUAGES["en"],
            )["name"],
            threshold=float(
                chat["threshold"]
            ),
            action=t(
                lang,
                f"action_{chat['action']}",
            ),
            warn_limit=int(
                chat["warn_limit"]
            ),
            escalation=t(
                lang,
                f"esc_{chat['escalation']}",
            ),
            mute=int(
                chat["mute_minutes"]
            ),
            custom=(
                "yes"
                if chat["custom_message"]
                else "no"
            ),
        )
        + t(
            lang,
            "settings_admin_line",
            admin_moderation=(t(lang,"admin_mod_on") if chat.get("moderate_admins") else t(lang,"admin_mod_off")),
        )
    )
