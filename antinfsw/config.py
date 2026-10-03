from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)

MODEL_ID = os.getenv("MODEL_ID", "Falconsai/nsfw_image_detection")
DB_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("MYSQL_PORT", "3306") or 3306)
DB_NAME = os.getenv("MYSQL_DATABASE", "antinfsw")
DB_USER = os.getenv("MYSQL_USER", "antinfsw")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

DEFAULT_THRESHOLD = float(os.getenv("DEFAULT_THRESHOLD", "0.50"))
DEFAULT_ACTION = os.getenv("DEFAULT_ACTION", "delete")
DEFAULT_WARN_LIMIT = int(os.getenv("DEFAULT_WARN_LIMIT", "3") or 3)
DEFAULT_MUTE_MINUTES = int(os.getenv("DEFAULT_MUTE_MINUTES", "10") or 10)
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
MODERATE_ADMINS_DEFAULT = os.getenv("MODERATE_ADMINS_DEFAULT", "true").lower() in {"1", "true", "yes", "on"}

CACHE_MAX_ENTRIES = int(os.getenv("CACHE_MAX_ENTRIES", "100000") or 100000)
INFERENCE_BATCH_SIZE = int(os.getenv("INFERENCE_BATCH_SIZE", "8") or 8)
INFERENCE_BATCH_WAIT_MS = int(os.getenv("INFERENCE_BATCH_WAIT_MS", "60") or 60)
VIDEO_MAX_FRAMES = int(os.getenv("VIDEO_MAX_FRAMES", "32") or 32)
GIF_MAX_FRAMES = int(os.getenv("GIF_MAX_FRAMES", "32") or 32)
TGS_MAX_FRAMES = int(os.getenv("TGS_MAX_FRAMES", "32") or 32)
MAX_VIDEO_DURATION_SECONDS = float(os.getenv("MAX_VIDEO_DURATION_SECONDS", "300"))
FRAME_MAX_SIDE = int(os.getenv("FRAME_MAX_SIDE", "896") or 896)
IMAGE_TTA = os.getenv("IMAGE_TTA", "true").lower() in {"1", "true", "yes", "on"}
FRAME_TOPK_PERCENT = float(os.getenv("FRAME_TOPK_PERCENT", "0.30"))
MAX_MEDIA_BYTES = int(os.getenv("MAX_MEDIA_BYTES", str(20 * 1024 * 1024)) or 20 * 1024 * 1024)
DETECTOR_CACHE_VERSION = os.getenv("DETECTOR_CACHE_VERSION", "2026-10-02-v6-strong-ensemble")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_SCHEMA = PROJECT_ROOT / "database" / "db.sql"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{BOT_TOKEN}" if BOT_TOKEN else ""

# LANGUAGE CONFIGURATION
# ============================================================

LANGUAGES = {
    "en": {
        "name": "English",
        "flag": "🇬🇧",
    },
    "fa": {
        "name": "فارسی",
        "flag": "🇮🇷",
    },
    "ar": {
        "name": "العربية",
        "flag": "🇸🇦",
    },
    "ru": {
        "name": "Русский",
        "flag": "🇷🇺",
    },
    "de": {
        "name": "Deutsch",
        "flag": "🇩🇪",
    },
    "fr": {
        "name": "Français",
        "flag": "🇫🇷",
    },
    "zh": {
        "name": "中文",
        "flag": "🇨🇳",
    },
    "ja": {
        "name": "日本語",
        "flag": "🇯🇵",
    },
}

ACTIONS = (
    "delete",
    "warn",
    "mute",
    "kick",
    "ban",
)

ESCALATIONS = (
    "none",
    "mute",
    "kick",
    "ban",
)

THRESHOLDS = tuple(i / 10 for i in range(1, 11))

WARN_LIMITS = (
    2,
    3,
    4,
    5,
)

MUTE_DURATIONS = (
    5,
    10,
    30,
    60,
    180,
    1440,
)


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "start_choose": "Choose your language to continue.",
        "start_title": "NSFW Guard",
        "start_body": (
            "I help protect groups by detecting likely NSFW images, "
            "stickers, animations and video frames.\n\n"
            "Add me to a group and give me permission to delete messages "
            "and restrict members for the moderation actions you select."
        ),
        "add_group": "➕ Add me to a group",
        "help": (
            "Use /start in private chat to choose your language.\n\n"
            "In a group, administrators can use /settings to configure "
            "detection, moderation actions and the response message.\n\n"
            "Required bot rights depend on the selected action: delete "
            "messages and, for restrictions, restrict members."
        ),
        "private_safe": (
            "✅ No NSFW content detected.\n"
            "Confidence: {confidence:.1%}"
        ),
        "private_nsfw": (
            "⚠️ Likely NSFW content detected.\n"
            "Confidence: {confidence:.1%}"
        ),
        "group_detected": (
            "⚠️ {mention}, NSFW content was detected and removed."
        ),
        "group_enabled": "🟢 NSFW protection: enabled",
        "group_disabled": "🔴 NSFW protection: disabled",
        "settings_title": "⚙️ NSFW Guard Settings",
        "settings_summary": (
            "Protection: {enabled}\n"
            "Language: {language}\n"
            "Threshold: {threshold:.0%}\n"
            "Action: {action}\n"
            "Warn limit: {warn_limit}\n"
            "Escalation: {escalation}\n"
            "Mute duration: {mute} min\n"
            "Custom message: {custom}"
        ),
        "settings_admin_line": "\nAdmin moderation: {admin_moderation}",
        "btn_toggle": "Protection: {state}",
        "btn_language": "🌐 Language",
        "btn_threshold": "🎚 Threshold",
        "btn_action": "🛡 Action",
        "btn_warn": "⚠️ Warn limit",
        "btn_escalation": "⛔ Escalation",
        "btn_mute": "🔇 Mute duration",
        "btn_message": "✏️ Custom message",
        "btn_reset_message": "↩️ Reset message",
        "btn_back": "◀️ Back",
        "pick_language": "Choose the group language.",
        "pick_threshold": (
            "Choose the NSFW confidence threshold."
        ),
        "pick_action": (
            "Choose what happens after NSFW content is detected."
        ),
        "pick_warn": (
            "Choose how many warnings trigger escalation."
        ),
        "pick_escalation": (
            "Choose the action after the warning limit is reached."
        ),
        "pick_mute": "Choose the mute duration.",
        "action_delete": "Delete message",
        "action_warn": "Warn user",
        "action_mute": "Delete + mute",
        "action_kick": "Delete + remove",
        "action_ban": "Delete + ban",
        "esc_none": "No escalation",
        "esc_mute": "Mute",
        "esc_kick": "Remove",
        "esc_ban": "Ban",
        "custom_help": (
            "Send /setmessage followed by the message you want the bot "
            "to send after a detection.\n\n"
            "Supported placeholders: {mention}, {confidence}, {action}\n"
            "Example:\n"
            "/setmessage ⚠️ {mention}, this content is not allowed here."
        ),
        "custom_saved": "✅ Custom moderation message updated.",
        "custom_reset": (
            "✅ Custom moderation message reset to the default."
        ),
        "admin_only": (
            "Only group administrators can change these settings."
        ),
        "group_only": (
            "This command is available in groups and supergroups."
        ),
        "bot_rights": (
            "I need administrator permission in this group. "
            "For deletion I need “Delete Messages”; for mute/remove/ban "
            "I also need “Restrict Members”."
        ),
        "invalid_command": (
            "Unknown command. Use /settings or /help."
        ),
        "stats": (
            "📊 Stats\n\n"
            "Checked: {checked}\n"
            "Detected NSFW: {nsfw}\n"
            "Protected groups: {groups}\n"
            "Known users: {users}"
        ),
        "action_delete": "delete",
        "action_warn": "warn",
        "action_mute": "mute",
        "action_kick": "remove",
        "action_ban": "ban",
        "action_failed": (
            "⚠️ Detection succeeded, but I could not complete the "
            "configured moderation action. Please check my admin permissions."
        ),
        "media_too_large": (
            "⚠️ I couldn't inspect this file because it is too large "
            "for the Telegram Bot API download limit."
        ),
        "unsupported_media": (
            "I can inspect photos, images sent as files, static stickers, "
            "animations and videos."
        ),
        "btn_admin_moderation": "👮 Moderate admins: {state}",
        "admin_mod_on": "enabled",
        "admin_mod_off": "disabled",
        "free_saved": "✅ User {mention} is now exempt from NSFW moderation in this group.",
        "free_removed": "✅ User {mention} is no longer exempt.",
        "free_usage": "Reply to a user's message with /free or /unfree, or provide their numeric user ID.",
        "blockmedia_saved": "✅ This exact media is now blocked in this group.",
        "blockmedia_removed": "✅ This exact media is no longer blocked.",
        "blockmedia_usage": "Reply to the media with /blockmedia or /unblockmedia.",
        "media_blocked": "⛔ This media is blocked in this group.",
        "group_detail_stats": "📊 Group stats\n\nChecked: {checked}\nNSFW: {nsfw}\nActions: {actions}\nExempt users: {exempt}\nBlocked media: {blocked}",
        "owner_only": "This command is restricted to the bot owner.",
        "owner_panel": "👑 <b>Owner panel</b>\n\n/ownerstats — global statistics\n/groups — active groups\n/sendgroup &lt;chat_id&gt; &lt;text&gt; — send to one group\n/broadcastgroups &lt;text&gt; — send to active groups\n/broadcastusers &lt;text&gt; — send to started users\n\nReply to any message to copy it instead of sending text.",
        "owner_stats": "👑 <b>Owner statistics</b>\n\nGroups: {groups}\nActive groups: {active_groups}\nUsers: {users}\nStarted users: {started_users}\nExempt users: {exempt_users}\nBlocked media: {blocked_media}\nChecked: {checked}\nNSFW: {nsfw}\nActions: {actions}",
        "owner_groups": "👑 <b>Active groups</b>\n{rows}",
        "owner_broadcast_result": "✅ Sent: {sent}\n⚠️ Failed: {failed}",
        "owner_send_usage": "Usage: /sendgroup &lt;chat_id&gt; &lt;text&gt; or reply to a message with /sendgroup &lt;chat_id&gt;.",
        "owner_broadcast_usage": "Usage: /broadcastgroups &lt;text&gt; or reply to a message with /broadcastgroups. Same for /broadcastusers.",

    },

    "fa": {
        "start_choose": "برای ادامه زبان موردنظر را انتخاب کنید.",
        "start_title": "NSFW Guard",
        "start_body": (
            "من برای محافظت از گروه‌ها، تصاویر، استیکرهای ثابت، "
            "انیمیشن‌ها و فریم‌های ویدیو را از نظر احتمال NSFW بررسی می‌کنم.\n\n"
            "مرا به گروه اضافه کنید و بر اساس تنظیمات انتخابی، دسترسی حذف "
            "پیام و محدود کردن اعضا را بدهید."
        ),
        "add_group": "➕ افزودن به گروه",
        "help": (
            "در چت خصوصی با /start زبان را انتخاب کنید.\n\n"
            "در گروه، مدیران می‌توانند با /settings تشخیص، مجازات‌ها "
            "و متن پاسخ را تنظیم کنند.\n\n"
            "بسته به مجازات انتخابی، ربات به دسترسی حذف پیام و برای "
            "محدودسازی اعضا به دسترسی محدودکردن اعضا نیاز دارد."
        ),
        "private_safe": (
            "✅ محتوای NSFW شناسایی نشد.\n"
            "اطمینان: {confidence:.1%}"
        ),
        "private_nsfw": (
            "⚠️ احتمال زیاد NSFW بودن محتوا شناسایی شد.\n"
            "اطمینان: {confidence:.1%}"
        ),
        "group_detected": (
            "⚠️ {mention} محتوای NSFW شناسایی و حذف شد."
        ),
        "group_enabled": "🟢 محافظت NSFW: فعال",
        "group_disabled": "🔴 محافظت NSFW: غیرفعال",
        "settings_title": "⚙️ تنظیمات NSFW Guard",
        "settings_summary": (
            "محافظت: {enabled}\n"
            "زبان: {language}\n"
            "آستانه: {threshold:.0%}\n"
            "اقدام: {action}\n"
            "حد اخطار: {warn_limit}\n"
            "اقدام نهایی: {escalation}\n"
            "مدت سکوت: {mute} دقیقه\n"
            "پیام اختصاصی: {custom}"
        ),
        "btn_toggle": "محافظت: {state}",
        "btn_language": "🌐 زبان",
        "btn_threshold": "🎚 آستانه",
        "btn_action": "🛡 اقدام",
        "btn_warn": "⚠️ حد اخطار",
        "btn_escalation": "⛔ اقدام نهایی",
        "btn_mute": "🔇 مدت سکوت",
        "btn_message": "✏️ پیام اختصاصی",
        "btn_reset_message": "↩️ بازنشانی پیام",
        "btn_back": "◀️ بازگشت",
        "pick_language": "زبان گروه را انتخاب کنید.",
        "pick_threshold": (
            "آستانه اطمینان تشخیص NSFW را انتخاب کنید."
        ),
        "pick_action": (
            "بعد از شناسایی محتوای NSFW چه اقدامی انجام شود؟"
        ),
        "pick_warn": (
            "تعداد اخطار قبل از اقدام نهایی را انتخاب کنید."
        ),
        "pick_escalation": (
            "بعد از رسیدن به حد اخطار چه اقدامی انجام شود؟"
        ),
        "pick_mute": "مدت محدودیت ارسال پیام را انتخاب کنید.",
        "action_delete": "حذف پیام",
        "action_warn": "اخطار به کاربر",
        "action_mute": "حذف + سکوت",
        "action_kick": "حذف + اخراج",
        "action_ban": "حذف + بن",
        "esc_none": "بدون اقدام نهایی",
        "esc_mute": "سکوت",
        "esc_kick": "اخراج",
        "esc_ban": "بن",
        "custom_help": (
            "پیام موردنظر را با /setmessage بفرستید.\n\n"
            "متغیرهای قابل استفاده: {mention}، {confidence}، {action}\n"
            "مثال:\n"
            "/setmessage ⚠️ {mention}، این محتوا در این گروه مجاز نیست."
        ),
        "custom_saved": "✅ پیام اختصاصی ذخیره شد.",
        "custom_reset": "✅ پیام اختصاصی به حالت پیش‌فرض برگشت.",
        "admin_only": (
            "فقط مدیران گروه می‌توانند این تنظیمات را تغییر دهند."
        ),
        "group_only": (
            "این دستور فقط داخل گروه یا سوپرگروه در دسترس است."
        ),
        "bot_rights": (
            "برای فعالیت صحیح باید در گروه ادمین باشم. "
            "برای حذف، دسترسی «حذف پیام‌ها» و برای سکوت/اخراج/بن، "
            "دسترسی «محدود کردن اعضا» لازم است."
        ),
        "invalid_command": (
            "دستور ناشناخته است. از /settings یا /help استفاده کنید."
        ),
        "stats": (
            "📊 آمار\n\n"
            "بررسی‌شده: {checked}\n"
            "NSFW شناسایی‌شده: {nsfw}\n"
            "گروه‌های محافظت‌شده: {groups}\n"
            "کاربران شناخته‌شده: {users}"
        ),
        "action_delete": "حذف",
        "action_warn": "اخطار",
        "action_mute": "سکوت",
        "action_kick": "اخراج",
        "action_ban": "بن",
        "action_failed": (
            "⚠️ تشخیص انجام شد اما اقدام تنظیم‌شده اجرا نشد. "
            "دسترسی‌های ادمین ربات را بررسی کنید."
        ),
        "media_too_large": (
            "⚠️ این فایل از محدودیت دانلود ربات تلگرام بزرگ‌تر است."
        ),
        "unsupported_media": (
            "می‌توانم عکس، تصویر به‌صورت فایل، استیکر ثابت، "
            "انیمیشن و ویدیو را بررسی کنم."
        ),
        "btn_admin_moderation": "👮 بررسی ادمین‌ها: {state}",
        "settings_admin_line": "\nبررسی ادمین‌ها: {admin_moderation}",
        "admin_mod_on": "فعال",
        "admin_mod_off": "غیرفعال",
        "free_saved": "✅ کاربر {mention} از بررسی NSFW این گروه معاف شد.",
        "free_removed": "✅ معافیت کاربر {mention} برداشته شد.",
        "free_usage": "روی پیام کاربر /free یا /unfree را ریپلای کنید؛ یا آیدی عددی بدهید.",
        "blockmedia_saved": "✅ این رسانه دقیقاً در این گروه مسدود شد.",
        "blockmedia_removed": "✅ مسدودی این رسانه برداشته شد.",
        "blockmedia_usage": "روی رسانه /blockmedia یا /unblockmedia را ریپلای کنید.",
        "media_blocked": "⛔ این رسانه در این گروه مسدود شده است.",
        "group_detail_stats": "📊 آمار گروه\n\nبررسی: {checked}\nNSFW: {nsfw}\nاقدامات: {actions}\nکاربران آزاد: {exempt}\nرسانه‌های مسدود: {blocked}",
        "owner_only": "این دستور فقط برای مالک ربات است.",
        "owner_panel": "👑 <b>پنل مالک</b>\n\n/ownerstats — آمار کلی\n/groups — گروه‌های فعال\n/sendgroup &lt;chat_id&gt; &lt;text&gt; — ارسال به یک گروه\n/broadcastgroups &lt;text&gt; — ارسال به گروه‌ها\n/broadcastusers &lt;text&gt; — ارسال به کاربران استارت‌زده\n\nبرای کپی یک پیام، روی همان پیام ریپلای کنید.",
        "owner_stats": "👑 <b>آمار مالک</b>\n\nگروه‌ها: {groups}\nگروه‌های فعال: {active_groups}\nکاربران: {users}\nاستارت‌زده: {started_users}\nآزاد: {exempt_users}\nرسانه مسدود: {blocked_media}\nبررسی: {checked}\nNSFW: {nsfw}\nاقدامات: {actions}",
        "owner_groups": "👑 <b>گروه‌های فعال</b>\n{rows}",
        "owner_broadcast_result": "✅ ارسال شد: {sent}\n⚠️ ناموفق: {failed}",
        "owner_send_usage": "استفاده: /sendgroup &lt;chat_id&gt; &lt;text&gt; یا روی یک پیام ریپلای کنید و /sendgroup &lt;chat_id&gt; بزنید.",
        "owner_broadcast_usage": "استفاده: /broadcastgroups &lt;text&gt; یا روی پیام ریپلای کنید. برای /broadcastusers نیز مشابه است.",

    },

    "ar": {
        "start_choose": "اختر لغتك للمتابعة.",
        "start_title": "NSFW Guard",
        "start_body": (
            "أساعد على حماية المجموعات عبر اكتشاف المحتوى الحساس "
            "المحتمل في الصور والملصقات الثابتة والرسوم المتحركة وإطارات الفيديو.\n\n"
            "أضفني إلى مجموعة ومنحني صلاحيات حذف الرسائل وتقييد الأعضاء "
            "حسب الإعدادات التي تختارها."
        ),
        "add_group": "➕ أضفني إلى مجموعة",
        "help": (
            "استخدم /start في الخاص لاختيار اللغة.\n\n"
            "يمكن للمشرفين استخدام /settings داخل المجموعة لضبط "
            "الكشف والإجراءات ورسالة التنبيه."
        ),
        "private_safe": (
            "✅ لم يتم اكتشاف محتوى NSFW.\n"
            "الثقة: {confidence:.1%}"
        ),
        "private_nsfw": (
            "⚠️ تم اكتشاف محتوى يُرجح أنه NSFW.\n"
            "الثقة: {confidence:.1%}"
        ),
        "group_detected": (
            "⚠️ {mention} تم اكتشاف محتوى NSFW وحذفه."
        ),
        "group_enabled": "🟢 حماية NSFW: مفعلة",
        "group_disabled": "🔴 حماية NSFW: معطلة",
        "settings_title": "⚙️ إعدادات NSFW Guard",
        "settings_summary": (
            "الحماية: {enabled}\n"
            "اللغة: {language}\n"
            "العتبة: {threshold:.0%}\n"
            "الإجراء: {action}\n"
            "حد التحذيرات: {warn_limit}\n"
            "التصعيد: {escalation}\n"
            "مدة الكتم: {mute} دقيقة\n"
            "رسالة مخصصة: {custom}"
        ),
        "btn_toggle": "الحماية: {state}",
        "btn_language": "🌐 اللغة",
        "btn_threshold": "🎚 العتبة",
        "btn_action": "🛡 الإجراء",
        "btn_warn": "⚠️ حد التحذيرات",
        "btn_escalation": "⛔ التصعيد",
        "btn_mute": "🔇 مدة الكتم",
        "btn_message": "✏️ رسالة مخصصة",
        "btn_reset_message": "↩️ إعادة الرسالة الافتراضية",
        "btn_back": "◀️ رجوع",
        "pick_language": "اختر لغة المجموعة.",
        "pick_threshold": "اختر عتبة الثقة.",
        "pick_action": (
            "اختر ما يحدث بعد اكتشاف محتوى NSFW."
        ),
        "pick_warn": (
            "اختر عدد التحذيرات قبل التصعيد."
        ),
        "pick_escalation": (
            "اختر الإجراء بعد بلوغ حد التحذيرات."
        ),
        "pick_mute": "اختر مدة الكتم.",
        "action_delete": "حذف الرسالة",
        "action_warn": "تحذير المستخدم",
        "action_mute": "حذف + كتم",
        "action_kick": "حذف + إزالة",
        "action_ban": "حذف + حظر",
        "esc_none": "بدون تصعيد",
        "esc_mute": "كتم",
        "esc_kick": "إزالة",
        "esc_ban": "حظر",
        "custom_help": (
            "أرسل /setmessage متبوعًا بالرسالة التي تريدها.\n\n"
            "المتغيرات: {mention}، {confidence}، {action}"
        ),
        "custom_saved": "✅ تم تحديث الرسالة المخصصة.",
        "custom_reset": "✅ تمت إعادة الرسالة الافتراضية.",
        "admin_only": (
            "فقط مشرفو المجموعة يمكنهم تغيير هذه الإعدادات."
        ),
        "group_only": (
            "هذا الأمر متاح داخل المجموعات فقط."
        ),
        "bot_rights": (
            "أحتاج إلى صلاحية مشرف. للحذف أحتاج حذف الرسائل، "
            "وللكتم/الإزالة/الحظر أحتاج تقييد الأعضاء."
        ),
        "invalid_command": (
            "أمر غير معروف. استخدم /settings أو /help."
        ),
        "stats": (
            "📊 الإحصائيات\n\n"
            "تم الفحص: {checked}\n"
            "NSFW المكتشف: {nsfw}\n"
            "المجموعات المحمية: {groups}\n"
            "المستخدمون: {users}"
        ),
        "action_delete": "حذف",
        "action_warn": "تحذير",
        "action_mute": "كتم",
        "action_kick": "إزالة",
        "action_ban": "حظر",
        "action_failed": (
            "⚠️ تم الكشف لكن تعذر تنفيذ الإجراء. "
            "تحقق من صلاحيات البوت."
        ),
        "media_too_large": (
            "⚠️ الملف أكبر من حد تنزيل Telegram Bot API."
        ),
        "unsupported_media": (
            "يمكنني فحص الصور والصور كملفات والملصقات الثابتة "
            "والرسوم المتحركة والفيديو."
        ),
    },

    "ru": {
        "start_choose": "Выберите язык для продолжения.",
        "start_title": "NSFW Guard",
        "start_body": (
            "Я помогаю защищать группы, обнаруживая возможный "
            "NSFW-контент на изображениях, стикерах, анимациях и кадрах видео.\n\n"
            "Добавьте меня в группу и выдайте права на удаление сообщений "
            "и ограничение участников согласно выбранным настройкам."
        ),
        "add_group": "➕ Добавить в группу",
        "help": (
            "В личном чате используйте /start для выбора языка.\n\n"
            "В группе администраторы могут использовать /settings для "
            "настройки проверки, действий и текста ответа."
        ),
        "private_safe": (
            "✅ NSFW-контент не обнаружен.\n"
            "Уверенность: {confidence:.1%}"
        ),
        "private_nsfw": (
            "⚠️ Обнаружен контент с высокой вероятностью NSFW.\n"
            "Уверенность: {confidence:.1%}"
        ),
        "group_detected": (
            "⚠️ {mention}, NSFW-контент обнаружен и удалён."
        ),
        "group_enabled": "🟢 Защита NSFW: включена",
        "group_disabled": "🔴 Защита NSFW: выключена",
        "settings_title": "⚙️ Настройки NSFW Guard",
        "settings_summary": (
            "Защита: {enabled}\n"
            "Язык: {language}\n"
            "Порог: {threshold:.0%}\n"
            "Действие: {action}\n"
            "Лимит предупреждений: {warn_limit}\n"
            "Эскалация: {escalation}\n"
            "Мут: {mute} мин\n"
            "Свой текст: {custom}"
        ),
        "btn_toggle": "Защита: {state}",
        "btn_language": "🌐 Язык",
        "btn_threshold": "🎚 Порог",
        "btn_action": "🛡 Действие",
        "btn_warn": "⚠️ Лимит предупреждений",
        "btn_escalation": "⛔ Эскалация",
        "btn_mute": "🔇 Длительность мута",
        "btn_message": "✏️ Свой текст",
        "btn_reset_message": "↩️ Сбросить текст",
        "btn_back": "◀️ Назад",
        "pick_language": "Выберите язык группы.",
        "pick_threshold": "Выберите порог уверенности.",
        "pick_action": (
            "Выберите действие после обнаружения NSFW."
        ),
        "pick_warn": (
            "Выберите число предупреждений до эскалации."
        ),
        "pick_escalation": (
            "Выберите действие после лимита предупреждений."
        ),
        "pick_mute": "Выберите длительность мута.",
        "action_delete": "Удалить сообщение",
        "action_warn": "Предупредить",
        "action_mute": "Удалить + мут",
        "action_kick": "Удалить + удалить пользователя",
        "action_ban": "Удалить + заблокировать",
        "esc_none": "Без эскалации",
        "esc_mute": "Мут",
        "esc_kick": "Удаление",
        "esc_ban": "Блокировка",
        "custom_help": (
            "Отправьте /setmessage и новый текст.\n\n"
            "Переменные: {mention}, {confidence}, {action}"
        ),
        "custom_saved": "✅ Свой текст обновлён.",
        "custom_reset": "✅ Возвращён текст по умолчанию.",
        "admin_only": (
            "Только администраторы группы могут изменять эти настройки."
        ),
        "group_only": (
            "Эта команда доступна только в группе."
        ),
        "bot_rights": (
            "Мне нужны права администратора. Для удаления — удаление "
            "сообщений; для мута/удаления/бана — ограничение участников."
        ),
        "invalid_command": (
            "Неизвестная команда. Используйте /settings или /help."
        ),
        "stats": (
            "📊 Статистика\n\n"
            "Проверено: {checked}\n"
            "NSFW найдено: {nsfw}\n"
            "Защищённых групп: {groups}\n"
            "Пользователей: {users}"
        ),
        "action_delete": "удаление",
        "action_warn": "предупреждение",
        "action_mute": "мут",
        "action_kick": "удаление",
        "action_ban": "бан",
        "action_failed": (
            "⚠️ Контент обнаружен, но действие не выполнено. "
            "Проверьте права бота."
        ),
        "media_too_large": (
            "⚠️ Файл превышает лимит скачивания Telegram Bot API."
        ),
        "unsupported_media": (
            "Я могу проверять фото, изображения как файлы, "
            "обычные стикеры, анимации и видео."
        ),
    },

    "de": {
        "start_choose": (
            "Wähle eine Sprache, um fortzufahren."
        ),
        "start_title": "NSFW Guard",
        "start_body": (
            "Ich helfe beim Schutz von Gruppen, indem ich wahrscheinliche "
            "NSFW-Inhalte in Bildern, Stickern, Animationen und Videoframes erkenne.\n\n"
            "Füge mich zu einer Gruppe hinzu und gib mir je nach Einstellung "
            "die Rechte zum Löschen von Nachrichten und Einschränken von Mitgliedern."
        ),
        "add_group": "➕ Zur Gruppe hinzufügen",
        "help": (
            "Nutze /start im privaten Chat zur Sprachauswahl.\n\n"
            "Gruppenadministratoren können mit /settings Erkennung, "
            "Maßnahmen und Antworttext konfigurieren."
        ),
        "private_safe": (
            "✅ Kein NSFW-Inhalt erkannt.\n"
            "Sicherheit: {confidence:.1%}"
        ),
        "private_nsfw": (
            "⚠️ Wahrscheinlicher NSFW-Inhalt erkannt.\n"
            "Sicherheit: {confidence:.1%}"
        ),
        "group_detected": (
            "⚠️ {mention}, NSFW-Inhalt wurde erkannt und entfernt."
        ),
        "group_enabled": "🟢 NSFW-Schutz: aktiviert",
        "group_disabled": "🔴 NSFW-Schutz: deaktiviert",
        "settings_title": "⚙️ NSFW Guard Einstellungen",
        "settings_summary": (
            "Schutz: {enabled}\n"
            "Sprache: {language}\n"
            "Schwelle: {threshold:.0%}\n"
            "Aktion: {action}\n"
            "Warnlimit: {warn_limit}\n"
            "Eskalation: {escalation}\n"
            "Mute: {mute} Min.\n"
            "Eigener Text: {custom}"
        ),
        "btn_toggle": "Schutz: {state}",
        "btn_language": "🌐 Sprache",
        "btn_threshold": "🎚 Schwelle",
        "btn_action": "🛡 Aktion",
        "btn_warn": "⚠️ Warnlimit",
        "btn_escalation": "⛔ Eskalation",
        "btn_mute": "🔇 Mute-Dauer",
        "btn_message": "✏️ Eigener Text",
        "btn_reset_message": "↩️ Text zurücksetzen",
        "btn_back": "◀️ Zurück",
        "pick_language": "Gruppensprache wählen.",
        "pick_threshold": (
            "NSFW-Vertrauenswert wählen."
        ),
        "pick_action": (
            "Was soll nach einer Erkennung passieren?"
        ),
        "pick_warn": (
            "Warnungen bis zur Eskalation wählen."
        ),
        "pick_escalation": (
            "Aktion nach dem Warnlimit wählen."
        ),
        "pick_mute": "Mute-Dauer wählen.",
        "action_delete": "Nachricht löschen",
        "action_warn": "Benutzer warnen",
        "action_mute": "Löschen + muten",
        "action_kick": "Löschen + entfernen",
        "action_ban": "Löschen + sperren",
        "esc_none": "Keine Eskalation",
        "esc_mute": "Muten",
        "esc_kick": "Entfernen",
        "esc_ban": "Sperren",
        "custom_help": (
            "Sende /setmessage gefolgt vom gewünschten Text.\n\n"
            "Platzhalter: {mention}, {confidence}, {action}"
        ),
        "custom_saved": (
            "✅ Eigener Moderationstext gespeichert."
        ),
        "custom_reset": (
            "✅ Standardtext wiederhergestellt."
        ),
        "admin_only": (
            "Nur Gruppenadministratoren können diese Einstellungen ändern."
        ),
        "group_only": (
            "Dieser Befehl ist nur in Gruppen verfügbar."
        ),
        "bot_rights": (
            "Ich brauche Administratorrechte. Zum Löschen „Nachrichten löschen“, "
            "zum Muten/Entfernen/Sperren zusätzlich „Mitglieder einschränken“."
        ),
        "invalid_command": (
            "Unbekannter Befehl. Nutze /settings oder /help."
        ),
        "stats": (
            "📊 Statistik\n\n"
            "Geprüft: {checked}\n"
            "NSFW erkannt: {nsfw}\n"
            "Geschützte Gruppen: {groups}\n"
            "Benutzer: {users}"
        ),
        "action_delete": "löschen",
        "action_warn": "warnen",
        "action_mute": "muten",
        "action_kick": "entfernen",
        "action_ban": "sperren",
        "action_failed": (
            "⚠️ Erkannt, aber die konfigurierte Maßnahme konnte nicht "
            "ausgeführt werden. Prüfe die Bot-Rechte."
        ),
        "media_too_large": (
            "⚠️ Die Datei ist größer als das Download-Limit der Telegram Bot API."
        ),
        "unsupported_media": (
            "Ich kann Fotos, Bilddateien, normale Sticker, "
            "Animationen und Videos prüfen."
        ),
    },

    "fr": {
        "start_choose": (
            "Choisissez votre langue pour continuer."
        ),
        "start_title": "NSFW Guard",
        "start_body": (
            "Je protège les groupes en détectant les contenus potentiellement "
            "NSFW dans les images, autocollants, animations et images vidéo.\n\n"
            "Ajoutez-moi à un groupe et accordez-moi les droits nécessaires "
            "pour supprimer les messages et limiter les membres."
        ),
        "add_group": "➕ Ajouter au groupe",
        "help": (
            "Utilisez /start en privé pour choisir la langue.\n\n"
            "Les administrateurs peuvent utiliser /settings dans un groupe "
            "pour configurer la détection, les actions et le message de réponse."
        ),
        "private_safe": (
            "✅ Aucun contenu NSFW détecté.\n"
            "Confiance : {confidence:.1%}"
        ),
        "private_nsfw": (
            "⚠️ Contenu probablement NSFW détecté.\n"
            "Confiance : {confidence:.1%}"
        ),
        "group_detected": (
            "⚠️ {mention}, contenu NSFW détecté et supprimé."
        ),
        "group_enabled": "🟢 Protection NSFW : activée",
        "group_disabled": "🔴 Protection NSFW : désactivée",
        "settings_title": "⚙️ Paramètres NSFW Guard",
        "settings_summary": (
            "Protection : {enabled}\n"
            "Langue : {language}\n"
            "Seuil : {threshold:.0%}\n"
            "Action : {action}\n"
            "Limite d'avertissements : {warn_limit}\n"
            "Escalade : {escalation}\n"
            "Mute : {mute} min\n"
            "Message personnalisé : {custom}"
        ),
        "btn_toggle": "Protection : {state}",
        "btn_language": "🌐 Langue",
        "btn_threshold": "🎚 Seuil",
        "btn_action": "🛡 Action",
        "btn_warn": "⚠️ Limite d'avertissements",
        "btn_escalation": "⛔ Escalade",
        "btn_mute": "🔇 Durée du mute",
        "btn_message": "✏️ Message personnalisé",
        "btn_reset_message": (
            "↩️ Réinitialiser le message"
        ),
        "btn_back": "◀️ Retour",
        "pick_language": (
            "Choisissez la langue du groupe."
        ),
        "pick_threshold": (
            "Choisissez le seuil de confiance."
        ),
        "pick_action": (
            "Choisissez l'action après détection."
        ),
        "pick_warn": (
            "Choisissez le nombre d'avertissements avant escalade."
        ),
        "pick_escalation": (
            "Choisissez l'action après la limite d'avertissements."
        ),
        "pick_mute": (
            "Choisissez la durée du mute."
        ),
        "action_delete": "Supprimer",
        "action_warn": "Avertir",
        "action_mute": "Supprimer + mute",
        "action_kick": "Supprimer + retirer",
        "action_ban": "Supprimer + bannir",
        "esc_none": "Aucune escalade",
        "esc_mute": "Mute",
        "esc_kick": "Retirer",
        "esc_ban": "Bannir",
        "custom_help": (
            "Envoyez /setmessage suivi du texte souhaité.\n\n"
            "Variables : {mention}, {confidence}, {action}"
        ),
        "custom_saved": (
            "✅ Message personnalisé mis à jour."
        ),
        "custom_reset": (
            "✅ Message par défaut restauré."
        ),
        "admin_only": (
            "Seuls les administrateurs peuvent modifier ces paramètres."
        ),
        "group_only": (
            "Cette commande est disponible uniquement dans les groupes."
        ),
        "bot_rights": (
            "J’ai besoin des droits administrateur. "
            "Pour supprimer : suppression des messages ; "
            "pour mute/retrait/ban : restriction des membres."
        ),
        "invalid_command": (
            "Commande inconnue. Utilisez /settings ou /help."
        ),
        "stats": (
            "📊 Statistiques\n\n"
            "Vérifiés : {checked}\n"
            "NSFW détectés : {nsfw}\n"
            "Groupes protégés : {groups}\n"
            "Utilisateurs : {users}"
        ),
        "action_delete": "suppression",
        "action_warn": "avertissement",
        "action_mute": "mute",
        "action_kick": "retrait",
        "action_ban": "ban",
        "action_failed": (
            "⚠️ Détection réussie, mais l’action configurée a échoué. "
            "Vérifiez les droits du bot."
        ),
        "media_too_large": (
            "⚠️ Le fichier dépasse la limite de téléchargement "
            "de Telegram Bot API."
        ),
        "unsupported_media": (
            "Je peux analyser les photos, fichiers image, "
            "stickers fixes, animations et vidéos."
        ),
    },

    "zh": {
        "start_choose": "请选择语言以继续。",
        "start_title": "NSFW Guard",
        "start_body": (
            "我可以帮助保护群组，检测图片、静态贴纸、动画和视频帧中的潜在 NSFW 内容。\n\n"
            "把我加入群组，并根据设置授予删除消息和限制成员所需的权限。"
        ),
        "add_group": "➕ 添加到群组",
        "help": (
            "在私聊中使用 /start 选择语言。\n\n"
            "群组管理员可以使用 /settings 配置检测、处罚动作和回复消息。"
        ),
        "private_safe": (
            "✅ 未检测到 NSFW 内容。\n"
            "置信度：{confidence:.1%}"
        ),
        "private_nsfw": (
            "⚠️ 检测到可能的 NSFW 内容。\n"
            "置信度：{confidence:.1%}"
        ),
        "group_detected": (
            "⚠️ {mention}，检测到 NSFW 内容，消息已删除。"
        ),
        "group_enabled": "🟢 NSFW 防护：已启用",
        "group_disabled": "🔴 NSFW 防护：已关闭",
        "settings_title": "⚙️ NSFW Guard 设置",
        "settings_summary": (
            "防护：{enabled}\n"
            "语言：{language}\n"
            "阈值：{threshold:.0%}\n"
            "动作：{action}\n"
            "警告次数：{warn_limit}\n"
            "升级动作：{escalation}\n"
            "禁言：{mute} 分钟\n"
            "自定义消息：{custom}"
        ),
        "btn_toggle": "防护：{state}",
        "btn_language": "🌐 语言",
        "btn_threshold": "🎚 阈值",
        "btn_action": "🛡 动作",
        "btn_warn": "⚠️ 警告上限",
        "btn_escalation": "⛔ 升级动作",
        "btn_mute": "🔇 禁言时间",
        "btn_message": "✏️ 自定义消息",
        "btn_reset_message": "↩️ 重置消息",
        "btn_back": "◀️ 返回",
        "pick_language": "选择群组语言。",
        "pick_threshold": (
            "选择 NSFW 置信度阈值。"
        ),
        "pick_action": (
            "选择检测到 NSFW 后的动作。"
        ),
        "pick_warn": (
            "选择升级前的警告次数。"
        ),
        "pick_escalation": (
            "选择达到警告上限后的动作。"
        ),
        "pick_mute": "选择禁言时长。",
        "action_delete": "删除消息",
        "action_warn": "警告用户",
        "action_mute": "删除 + 禁言",
        "action_kick": "删除 + 移除",
        "action_ban": "删除 + 封禁",
        "esc_none": "不升级",
        "esc_mute": "禁言",
        "esc_kick": "移除",
        "esc_ban": "封禁",
        "custom_help": (
            "发送 /setmessage 加上你希望发送的内容。\n\n"
            "变量：{mention}、{confidence}、{action}"
        ),
        "custom_saved": "✅ 自定义消息已更新。",
        "custom_reset": "✅ 已恢复默认消息。",
        "admin_only": (
            "只有群组管理员可以修改这些设置。"
        ),
        "group_only": (
            "此命令仅可在群组中使用。"
        ),
        "bot_rights": (
            "我需要管理员权限。删除需要“删除消息”，"
            "禁言/移除/封禁还需要“限制成员”。"
        ),
        "invalid_command": (
            "未知命令。请使用 /settings 或 /help。"
        ),
        "stats": (
            "📊 统计\n\n"
            "已检查：{checked}\n"
            "检测到 NSFW：{nsfw}\n"
            "受保护群组：{groups}\n"
            "用户：{users}"
        ),
        "action_delete": "删除",
        "action_warn": "警告",
        "action_mute": "禁言",
        "action_kick": "移除",
        "action_ban": "封禁",
        "action_failed": (
            "⚠️ 已检测到内容，但配置的动作执行失败。请检查机器人权限。"
        ),
        "media_too_large": (
            "⚠️ 文件超过 Telegram Bot API 的下载限制。"
        ),
        "unsupported_media": (
            "我可以检查照片、图片文件、普通贴纸、动画和视频。"
        ),
    },

    "ja": {
        "start_choose": (
            "続行する言語を選択してください。"
        ),
        "start_title": "NSFW Guard",
        "start_body": (
            "画像、静止ステッカー、アニメーション、動画フレームに"
            "含まれる可能性のある NSFW コンテンツを検出して、"
            "グループの安全管理を支援します。\n\n"
            "グループに追加し、必要に応じてメッセージ削除と"
            "メンバー制限の権限を与えてください。"
        ),
        "add_group": "➕ グループに追加",
        "help": (
            "プライベートチャットで /start を使って言語を選択します。\n\n"
            "グループ管理者は /settings で検出、対応、"
            "返信メッセージを設定できます。"
        ),
        "private_safe": (
            "✅ NSFW コンテンツは検出されませんでした。\n"
            "信頼度: {confidence:.1%}"
        ),
        "private_nsfw": (
            "⚠️ NSFW の可能性が高いコンテンツを検出しました。\n"
            "信頼度: {confidence:.1%}"
        ),
        "group_detected": (
            "⚠️ {mention}、NSFW コンテンツを検出して削除しました。"
        ),
        "group_enabled": "🟢 NSFW 保護: 有効",
        "group_disabled": "🔴 NSFW 保護: 無効",
        "settings_title": "⚙️ NSFW Guard 設定",
        "settings_summary": (
            "保護: {enabled}\n"
            "言語: {language}\n"
            "閾値: {threshold:.0%}\n"
            "アクション: {action}\n"
            "警告上限: {warn_limit}\n"
            "エスカレーション: {escalation}\n"
            "ミュート: {mute} 分\n"
            "カスタムメッセージ: {custom}"
        ),
        "btn_toggle": "保護: {state}",
        "btn_language": "🌐 言語",
        "btn_threshold": "🎚 閾値",
        "btn_action": "🛡 アクション",
        "btn_warn": "⚠️ 警告上限",
        "btn_escalation": "⛔ エスカレーション",
        "btn_mute": "🔇 ミュート時間",
        "btn_message": "✏️ カスタムメッセージ",
        "btn_reset_message": "↩️ リセット",
        "btn_back": "◀️ 戻る",
        "pick_language": (
            "グループの言語を選択してください。"
        ),
        "pick_threshold": (
            "NSFW 信頼度の閾値を選択してください。"
        ),
        "pick_action": (
            "NSFW 検出後のアクションを選択してください。"
        ),
        "pick_warn": (
            "エスカレーションまでの警告回数を選択してください。"
        ),
        "pick_escalation": (
            "警告上限到達後のアクションを選択してください。"
        ),
        "pick_mute": (
            "ミュート時間を選択してください。"
        ),
        "action_delete": "メッセージ削除",
        "action_warn": "ユーザー警告",
        "action_mute": "削除 + ミュート",
        "action_kick": "削除 + 追放",
        "action_ban": "削除 + BAN",
        "esc_none": "エスカレーションなし",
        "esc_mute": "ミュート",
        "esc_kick": "追放",
        "esc_ban": "BAN",
        "custom_help": (
            "/setmessage の後に送信したい文面を指定してください。\n\n"
            "変数: {mention}, {confidence}, {action}"
        ),
        "custom_saved": (
            "✅ カスタムメッセージを更新しました。"
        ),
        "custom_reset": (
            "✅ デフォルトメッセージに戻しました。"
        ),
        "admin_only": (
            "設定を変更できるのはグループ管理者だけです。"
        ),
        "group_only": (
            "このコマンドはグループでのみ使用できます。"
        ),
        "bot_rights": (
            "管理者権限が必要です。削除にはメッセージ削除、"
            "ミュート/追放/BAN にはメンバー制限が必要です。"
        ),
        "invalid_command": (
            "不明なコマンドです。/settings または /help を使用してください。"
        ),
        "stats": (
            "📊 統計\n\n"
            "チェック: {checked}\n"
            "NSFW 検出: {nsfw}\n"
            "保護グループ: {groups}\n"
            "ユーザー: {users}"
        ),
        "action_delete": "削除",
        "action_warn": "警告",
        "action_mute": "ミュート",
        "action_kick": "追放",
        "action_ban": "BAN",
        "action_failed": (
            "⚠️ 検出されましたが、設定したアクションを実行できませんでした。"
            "ボットの権限を確認してください。"
        ),
        "media_too_large": (
            "⚠️ ファイルが Telegram Bot API のダウンロード制限を超えています。"
        ),
        "unsupported_media": (
            "写真、画像ファイル、通常のステッカー、"
            "アニメーション、動画をチェックできます。"
        ),
    },
}


# ============================================================
