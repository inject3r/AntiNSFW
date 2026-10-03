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

class OwnerMixin:
            async def is_owner(self, user_id:int) -> bool:
                return int(user_id)==OWNER_ID

            def _target_user(message:dict[str,Any], arg:str) -> Optional[dict[str,Any]]:
                target=(message.get("reply_to_message") or {}).get("from") or {}
                if target.get("id"): return target
                if (arg or "").strip().isdigit(): return {"id":int(arg.strip()),"first_name":f"User {arg.strip()}"}
                return None

            async def _owner_lang(self,user_id:int)->str:
                return await self.db.get_user_language(user_id)

            async def owner_send(self,message:dict[str,Any],target:int,arg:str)->bool:
                reply=message.get("reply_to_message") or {}
                try:
                    if reply.get("message_id"):
                        await self.api.copy_message(target,int(message["chat"]["id"]),int(reply["message_id"]))
                    elif arg.strip():
                        await self.api.send_message(target,arg.strip())
                    else:
                        return False
                    return True
                except Exception as exc:
                    logging.warning("OWNER_SEND_FAILED target=%s error=%s",target,exc)
                    return False

            async def owner_guard(self,message:dict[str,Any])->tuple[bool,str,int]:
                uid=int(message.get("from",{}).get("id",0)); lang=await self._owner_lang(uid)
                if not await self.is_owner(uid):
                    await self.api.send_message(message["chat"]["id"],t(lang,"owner_only")); return False,lang,uid
                return True,lang,uid

            async def handle_owner_panel(self,message:dict[str,Any])->None:
                ok,lang,_=await self.owner_guard(message)
                if ok:
                    await self.api.send_message(
                        message["chat"]["id"],
                        await self._owner_dashboard_text(lang),
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                        reply_markup=self._owner_main_keyboard(lang),
                    )

            async def handle_owner_stats(self,message:dict[str,Any])->None:
                ok,lang,_=await self.owner_guard(message)
                if ok: await self.api.send_message(message["chat"]["id"],t(lang,"owner_stats",**(await self.db.owner_stats())),parse_mode="HTML")

            async def handle_owner_groups(self,message:dict[str,Any])->None:
                ok,lang,_=await self.owner_guard(message)
                if not ok:return
                groups=await self.db.list_active_groups()
                rows="\n".join(f"• {esc(g.get('title') or 'Untitled')} | <code>{g['chat_id']}</code> | {'ON' if g['enabled'] else 'OFF'} | checked={g['checked']} nsfw={g['nsfw']} actions={g['actions']}" for g in groups) or "(none)"
                target_chat=int(message["chat"]["id"])
                text=t(lang,"owner_groups",rows=rows)
                for start in range(0,len(text),3800):
                    await self.api.send_message(target_chat,text[start:start+3800],parse_mode="HTML")

            async def handle_owner_sendgroup(self,message:dict[str,Any],arg:str)->None:
                ok,lang,_=await self.owner_guard(message)
                if not ok:return
                parts=(arg or "").split(None,1)
                if not parts or not re.fullmatch(r"-?\d+",parts[0]):
                    await self.api.send_message(message["chat"]["id"],t(lang,"owner_send_usage"),parse_mode="HTML"); return
                success=await self.owner_send(message,int(parts[0]),parts[1] if len(parts)>1 else "")
                await self.api.send_message(message["chat"]["id"],"✅ Sent." if success else "⚠️ Failed.")

            async def handle_owner_broadcast(self,message:dict[str,Any],arg:str,users:bool)->None:
                ok,lang,_=await self.owner_guard(message)
                if not ok:return
                targets=await self.db.list_started_user_ids() if users else [int(g["chat_id"]) for g in await self.db.list_active_groups()]
                if not targets:
                    await self.api.send_message(message["chat"]["id"],"No targets."); return
                sent=failed=0
                for target in targets:
                    if await self.owner_send(message,target,arg):sent+=1
                    else:failed+=1
                    await asyncio.sleep(0.05)
                await self.api.send_message(message["chat"]["id"],t(lang,"owner_broadcast_result",sent=sent,failed=failed))

            def _owner_text(lang: str, key: str, **kwargs: Any) -> str:
                fa = {
                    "title": "👑 <b>مرکز فرماندهی مالک</b>",
                    "dashboard": "📊 داشبورد و سلامت ربات",
                    "groups": "👥 مدیریت گروه‌ها",
                    "broadcast": "📣 ارسال و Broadcast",
                    "search": "🔎 جستجوی گروه",
                    "system": "🧠 اطلاعات سیستم",
                    "back": "◀️ بازگشت",
                    "refresh": "🔄 بروزرسانی",
                    "group_info": "📋 اطلاعات کامل",
                    "group_stats": "📊 آمار گروه",
                    "group_admins": "👮 ادمین‌ها",
                    "group_members": "👥 کاربران مشاهده‌شده",
                    "group_settings": "⚙️ تنظیمات گروه",
                    "send_group": "📨 ارسال به این گروه",
                    "toggle_protection": "🛡 تغییر وضعیت حفاظت",
                    "toggle_admins": "👮 تغییر بررسی ادمین‌ها",
                    "leave": "🚪 خروج ربات از گروه",
                    "broadcast_groups": "📣 پیام به همه گروه‌ها",
                    "broadcast_users": "👤 پیام به کاربران /start کرده",
                    "cancel": "❌ لغو",
                    "prev": "⬅️ قبلی",
                    "next": "بعدی ➡️",
                    "public": "عمومی",
                    "private": "خصوصی",
                    "unknown": "نامشخص",
                    "not_available": "در دسترس نیست",
                    "prompt_group_search": "🔎 شناسه گروه، @username یا لینک عمومی را بفرست.",
                    "prompt_send": "📨 پیام متنی یا رسانه‌ای را همین‌جا بفرست تا ارسال شود.",
                    "prompt_broadcast_groups": "📣 پیام متنی یا رسانه‌ای را بفرست تا برای همه گروه‌های فعال ارسال شود.",
                    "prompt_broadcast_users": "👤 پیام متنی یا رسانه‌ای را بفرست تا برای کاربران ثبت‌شده ارسال شود.",
                    "cancelled": "✅ عملیات لغو شد.",
                    "done": "✅ انجام شد.",
                    "send_result": "✅ موفق: {sent}\n⚠️ ناموفق: {failed}",
                    "no_groups": "هیچ گروه فعالی ثبت نشده است.",
                    "members_note": "این بخش اعضایی را نشان می‌دهد که ربات پیامشان را دیده است؛ Bot API فهرست کامل اعضای گروه را در اختیار ربات قرار نمی‌دهد.",
                    "admin_note": "اطلاعات بیو/توضیحات خود گروه از API گرفته می‌شود؛ بیوی حساب شخصی ادمین از Bot API قابل دریافت نیست.",
                    "users": "👥 کاربران ربات", "audit": "📝 لاگ عملیات", "period": "📈 آمار زمانی", "test": "🧪 تست تشخیص",
                    "prompt_test": "یک عکس/استیکر/گیف/ویدیو را در همین چت بفرست تا فقط نتیجه تشخیص را نشان بدهم و اقدامی روی پیام انجام ندهم.",
                    "prompt_test_cancel": "لغو تست", "bot_permissions": "🔐 دسترسی‌های ربات", "exempt": "🆓 کاربران آزاد", "blocked": "🚫 رسانه‌های مسدود",
                    "group_audit": "📝 لاگ گروه", "group_health": "🩺 سلامت گروه", "daily": "امروز", "week": "۷ روز", "month": "۳۰ روز",
                    "user_search": "🔎 جستجوی کاربر", "user_groups": "🏢 گروه‌های کاربر", "user_warnings": "⚠️ اخطارهای کاربر",
                    "user_exemptions": "🆓 معافیت‌های کاربر", "user_activity": "📝 فعالیت کاربر", "user_send": "📨 ارسال پیام",
                    "user_language": "🌐 زبان کاربر", "user_block": "🚫 مسدودکردن پیام خصوصی", "user_unblock": "✅ رفع مسدودی پیام خصوصی",
                    "user_reset_warnings": "🧹 پاک‌کردن همه اخطارها", "user_note": "📝 یادداشت مالک", "prompt_user_search": "آیدی عددی، @username یا نام کاربر را بفرست.",
                    "prompt_user_note": "یادداشت داخلی مالک را بفرست (حداکثر ۱۲۰۰ کاراکتر).", "prompt_user_send": "پیام متنی یا رسانه‌ای را برای این کاربر بفرست.",
                    "user_reset_confirm": "⚠️ همه اخطارهای این کاربر در تمام گروه‌ها پاک شود؟", "user_reset_done": "✅ اخطارهای کاربر پاک شد.",
                }
                en = {
                    "title": "👑 <b>Owner Command Center</b>",
                    "dashboard": "📊 Dashboard & health",
                    "groups": "👥 Group management",
                    "broadcast": "📣 Send & broadcast",
                    "search": "🔎 Search group",
                    "system": "🧠 System info",
                    "back": "◀️ Back",
                    "refresh": "🔄 Refresh",
                    "group_info": "📋 Full information",
                    "group_stats": "📊 Group stats",
                    "group_admins": "👮 Administrators",
                    "group_members": "👥 Tracked users",
                    "group_settings": "⚙️ Group settings",
                    "send_group": "📨 Send to this group",
                    "toggle_protection": "🛡 Toggle protection",
                    "toggle_admins": "👮 Toggle admin moderation",
                    "leave": "🚪 Make bot leave",
                    "broadcast_groups": "📣 Message all groups",
                    "broadcast_users": "👤 Message started users",
                    "cancel": "❌ Cancel",
                    "prev": "⬅️ Prev",
                    "next": "Next ➡️",
                    "public": "Public",
                    "private": "Private",
                    "unknown": "Unknown",
                    "not_available": "Unavailable",
                    "prompt_group_search": "🔎 Send a chat ID, @username or public chat link.",
                    "prompt_send": "📨 Send text or media here and it will be delivered.",
                    "prompt_broadcast_groups": "📣 Send text or media to broadcast it to active groups.",
                    "prompt_broadcast_users": "👤 Send text or media to broadcast it to started users.",
                    "cancelled": "✅ Operation cancelled.",
                    "done": "✅ Done.",
                    "send_result": "✅ Success: {sent}\n⚠️ Failed: {failed}",
                    "no_groups": "No active groups are registered.",
                    "members_note": "This page shows users whose messages the bot has seen; the Bot API does not expose a complete group-member list to bots.",
                    "admin_note": "The group description is available from the API; a private administrator bio is not exposed by the Bot API.",
                    "users": "👥 Bot users", "audit": "📝 Audit logs", "period": "📈 Period stats", "test": "🧪 Detection test",
                    "prompt_test": "Send an image/sticker/GIF/video here for a detection-only test. No moderation action will be taken.",
                    "prompt_test_cancel": "Cancel test", "bot_permissions": "🔐 Bot permissions", "exempt": "🆓 Exempt users", "blocked": "🚫 Blocked media",
                    "group_audit": "📝 Group audit", "group_health": "🩺 Group health", "daily": "Today", "week": "7 days", "month": "30 days",
                    "user_search": "🔎 Search user", "user_groups": "🏢 User groups", "user_warnings": "⚠️ User warnings",
                    "user_exemptions": "🆓 User exemptions", "user_activity": "📝 User activity", "user_send": "📨 Send message",
                    "user_language": "🌐 User language", "user_block": "🚫 Block private bot access", "user_unblock": "✅ Unblock private bot access",
                    "user_reset_warnings": "🧹 Reset all warnings", "user_note": "📝 Owner note", "prompt_user_search": "Send a numeric ID, @username, or user name.",
                    "prompt_user_note": "Send an internal owner note (max 1200 characters).", "prompt_user_send": "Send text or media to this user.",
                    "user_reset_confirm": "⚠️ Reset all warnings for this user in every group?", "user_reset_done": "✅ User warnings reset.",
                }
                table = fa if lang == "fa" else en
                value = table.get(key, key)
                try:
                    return value.format(**kwargs)
                except Exception:
                    return value

            def _owner_button(text: str, data: str) -> dict[str, str]:
                return {"text": text, "callback_data": data}

            async def _owner_edit(
                self,
                callback: dict[str, Any],
                text: str,
                markup: dict[str, Any],
            ) -> None:
                message = callback.get("message") or {}
                chat = message.get("chat") or {}
                if not chat.get("id") or not message.get("message_id"):
                    return
                await self.api.edit_message(
                    int(chat["id"]),
                    int(message["message_id"]),
                    text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=markup,
                )

            def _owner_main_keyboard(self, lang: str) -> dict[str, Any]:
                return {"inline_keyboard": [
                    [self._owner_button("📊 داشبورد", "o:dash"), self._owner_button("🏢 گروه‌ها", "o:groups:0")],
                    [self._owner_button("👥 کاربران", "o:users:0"), self._owner_button("🔎 جستجوی کاربر", "o:usearch")],
                    [self._owner_button("📝 لاگ‌ها", "o:audit:0"), self._owner_button("📈 آمار زمانی", "o:period")],
                    [self._owner_button("📣 Broadcast", "o:broadcast"), self._owner_button("🔎 جستجو", "o:search")],
                    [self._owner_button("🧪 تست تشخیص", "o:test"), self._owner_button("🩺 سلامت سیستم", "o:system")],
                    [self._owner_button("🔄 بروزرسانی", "o:dash")],
                    [{"text":"👨‍💻 توسعه‌دهنده · @inject3r", "url":"https://t.me/inject3r"}],
                ]}

            async def _owner_dashboard_text(self, lang: str) -> str:
                stats = await self.db.owner_stats()
                uptime = max(0, int(time.monotonic() - self.started_at))
                h, rem = divmod(uptime, 3600); m, sec = divmod(rem, 60)
                groups = await self.db.list_active_groups()
                enabled = sum(1 for g in groups if g.get("enabled"))
                return (
                    f"{self._owner_text(lang,'title')}\n\n"
                    f"<b>{self._owner_text(lang,'dashboard')}</b>\n"
                    f"• Groups: <b>{stats['active_groups']}</b> (enabled {enabled})\n"
                    f"• Users started: <b>{stats['started_users']}</b>\n"
                    f"• Users blocked: <b>{stats.get('blocked_users', 0)}</b>\n"
                    f"• Checked: <b>{stats['checked']}</b>\n"
                    f"• NSFW detections: <b>{stats['nsfw']}</b>\n"
                    f"• Moderation actions: <b>{stats['actions']}</b>\n"
                    f"• Exempt users: <b>{stats['exempt_users']}</b>\n"
                    f"• Blocked media: <b>{stats['blocked_media']}</b>\n"
                    f"• Uptime: <b>{h}h {m}m {sec}s</b>\n"
                    f"• Device: <b>{esc(str(self.detector.device))}</b>\n"
                    f"• Detector: <code>{esc(self.detector.model_id)}</code>"
                )

            async def _owner_show_home(self, callback: dict[str, Any]) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid):
                    await self.api.answer_callback(callback.get("id",""), "Owner only")
                    return
                lang=await self._owner_lang(uid)
                await self.api.answer_callback(callback["id"])
                await self._owner_edit(callback, await self._owner_dashboard_text(lang), self._owner_main_keyboard(lang))

            async def _owner_group_list(self, callback: dict[str, Any], page: int = 0) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid):
                    await self.api.answer_callback(callback["id"], "Owner only"); return
                lang=await self._owner_lang(uid)
                groups=await self.db.list_active_groups()
                per_page=6
                page=max(0,min(int(page),(max(1,(len(groups)+per_page-1)//per_page)-1)))
                chunk=groups[page*per_page:(page+1)*per_page]
                rows=[]
                for g in chunk:
                    title=(g.get("title") or "Untitled").strip()
                    if len(title)>30: title=title[:27]+"…"
                    state="🟢" if g.get("enabled") else "🔴"
                    rows.append([self._owner_button(f"{state} {title}",f"o:g:{int(g['chat_id'])}")])
                if not rows: rows.append([self._owner_button(self._owner_text(lang,"refresh"),"o:groups:0")])
                nav=[]
                if page>0: nav.append(self._owner_button(self._owner_text(lang,"prev"),f"o:groups:{page-1}"))
                if (page+1)*per_page<len(groups): nav.append(self._owner_button(self._owner_text(lang,"next"),f"o:groups:{page+1}"))
                if nav: rows.append(nav)
                rows.append([self._owner_button(self._owner_text(lang,"back"),"o:home")])
                text=(f"{self._owner_text(lang,'title')}\n\n<b>{self._owner_text(lang,'groups')}</b>\n"
                      f"Page {page+1}/{max(1,(len(groups)+per_page-1)//per_page)}\n"
                      f"Total tracked groups: <b>{len(groups)}</b>")
                if not groups: text += f"\n\n{self._owner_text(lang,'no_groups')}"
                await self.api.answer_callback(callback["id"])
                await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_users_page(self, callback: dict[str, Any], page:int=0) -> None:
                uid=int((callback.get("from") or {}).get("id",0)); lang=await self._owner_lang(uid)
                users,total=await self.db.list_users(page,8)
                pages=max(1,(total+7)//8); page=max(0,min(page,pages-1))
                users,_=await self.db.list_users(page,8)
                lines=[]
                rows=[]
                for u in users:
                    name=((u.get("first_name") or "")+((" "+u.get("last_name")) if u.get("last_name") else "")).strip() or "User"
                    uname=(" @"+u.get("username")) if u.get("username") else ""
                    status=("🚫" if u.get("bot_blocked") else "🟢") + (" /start" if u.get("started") else "")
                    lines.append(f"• <b>{esc(name)}</b>{esc(uname)} {status}\n  <code>{u['user_id']}</code> · {esc(u.get('last_seen') or '—')}")
                    rows.append([self._owner_button(f"👤 {name[:30]}",f"o:u:{u['user_id']}")])
                nav=[]
                if page>0: nav.append(self._owner_button(self._owner_text(lang,"prev"),f"o:users:{page-1}"))
                if page+1<pages: nav.append(self._owner_button(self._owner_text(lang,"next"),f"o:users:{page+1}"))
                if nav: rows.append(nav)
                rows.append([self._owner_button(self._owner_text(lang,"user_search"),"o:usearch")])
                rows.append([self._owner_button(self._owner_text(lang,"back"),"o:home")])
                text=(f"{self._owner_text(lang,'title')}\n\n👥 <b>{self._owner_text(lang,'users')}</b>\n"
                      f"Page {page+1}/{pages} · Total <b>{total}</b>\n\n"+('\n'.join(lines) if lines else '—'))
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_user_detail(self, callback:dict[str,Any], user_id:int)->None:
                uid=int((callback.get("from") or {}).get("id",0)); lang=await self._owner_lang(uid); u=await self.db.get_user_summary(user_id)
                if not u:
                    await self.api.answer_callback(callback['id'],"User not found"); return
                name=((u.get('first_name') or '')+' '+(u.get('last_name') or '')).strip() or 'User'
                uname=("@"+u.get('username')) if u.get('username') else '—'
                blocked=bool(u.get('bot_blocked'))
                text=(
                    f"{self._owner_text(lang,'title')}\n\n👤 <b>مدیریت کامل کاربر</b>\n\n"
                    f"<b>{esc(name)}</b> · {esc(uname)}\n"
                    f"ID: <code>{user_id}</code>\n"
                    f"زبان: <b>{esc(u.get('language') or DEFAULT_LANGUAGE)}</b>\n"
                    f"/start: <b>{'✅' if u.get('started') else '—'}</b>\n"
                    f"دسترسی خصوصی ربات: <b>{'🚫 مسدود' if blocked else '✅ آزاد'}</b>\n"
                    f"اولین مشاهده: <b>{esc(u.get('first_seen') or '—')}</b>\n"
                    f"آخرین مشاهده: <b>{esc(u.get('last_seen') or '—')}</b>\n\n"
                    f"گروه‌های دیده‌شده: <b>{u['groups_count']}</b>\n"
                    f"تعداد پیام در گروه‌ها: <b>{u['messages_count']}</b>\n"
                    f"اخطارها: <b>{u['warning_count']}</b> در {u['warning_groups']} گروه\n"
                    f"معافیت‌ها: <b>{u['exempt_count']}</b>\n"
                    f"رویدادهای مرتبط: <b>{u['audit_count']}</b>\n"
                    f"یادداشت مالک: <b>{esc(u.get('owner_note') or '—')}</b>"
                )
                rows=[
                    [self._owner_button(self._owner_text(lang,"user_groups"),f"o:ug:{user_id}:0"), self._owner_button(self._owner_text(lang,"user_warnings"),f"o:uw:{user_id}:0")],
                    [self._owner_button(self._owner_text(lang,"user_exemptions"),f"o:ue:{user_id}:0"), self._owner_button(self._owner_text(lang,"user_activity"),f"o:ua:{user_id}:0")],
                    [self._owner_button(self._owner_text(lang,"user_language"),f"o:ul:{user_id}"), self._owner_button(self._owner_text(lang,"user_send"),f"o:usend:{user_id}")],
                    [self._owner_button(self._owner_text(lang,"user_unblock" if blocked else "user_block"),f"o:ub:{user_id}"), self._owner_button(self._owner_text(lang,"user_reset_warnings"),f"o:urw:{user_id}")],
                    [self._owner_button(self._owner_text(lang,"user_note"),f"o:un:{user_id}"), self._owner_button(self._owner_text(lang,"refresh"),f"o:u:{user_id}")],
                    [self._owner_button(self._owner_text(lang,"back"),"o:users:0")],
                ]
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_user_groups_page(self, callback:dict[str,Any], user_id:int, page:int=0)->None:
                uid=int((callback.get("from") or {}).get("id",0)); lang=await self._owner_lang(uid); rows_data,total=await self.db.list_user_groups(user_id,page,6); pages=max(1,(total+5)//6); page=max(0,min(page,pages-1)); rows_data,_=await self.db.list_user_groups(user_id,page,6)
                lines=[]; rows=[]
                for g in rows_data:
                    lines.append(f"• <b>{esc(g.get('title') or 'Untitled')}</b> · <code>{g['chat_id']}</code>\n  msgs <b>{g['message_count']}</b> · last {esc(g.get('last_seen') or '—')} · {'🟢' if g.get('bot_in_chat') else '🔴'}")
                    rows.append([self._owner_button(f"🏢 {(g.get('title') or 'Group')[:28]}",f"o:g:{g['chat_id']}")])
                nav=[]
                if page>0: nav.append(self._owner_button(self._owner_text(lang,"prev"),f"o:ug:{user_id}:{page-1}"))
                if page+1<pages: nav.append(self._owner_button(self._owner_text(lang,"next"),f"o:ug:{user_id}:{page+1}"))
                if nav: rows.append(nav)
                rows.append([self._owner_button("◀️ کاربر",f"o:u:{user_id}")])
                text=f"👤 <b>{self._owner_text(lang,'user_groups')}</b>\nUser: <code>{user_id}</code>\nPage {page+1}/{pages} · Total {total}\n\n"+('\\n'.join(lines) if lines else '—')
                text=text.replace('\\n','\n')
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_user_warnings_page(self, callback:dict[str,Any], user_id:int, page:int=0)->None:
                uid=int((callback.get("from") or {}).get("id",0)); lang=await self._owner_lang(uid); rows_data,total=await self.db.list_user_warnings(user_id,page,6); pages=max(1,(total+5)//6); page=max(0,min(page,pages-1)); rows_data,_=await self.db.list_user_warnings(user_id,page,6)
                lines=[]; rows=[]
                for r in rows_data:
                    title=esc(r.get('title') or 'Untitled'); lines.append(f"• <b>{title}</b> · <code>{r['chat_id']}</code> · اخطار: <b>{r['count']}</b> · {esc(r.get('updated_at') or '—')}")
                    rows.append([self._owner_button(f"🧹 پاک {title[:20]}",f"o:uwr:{user_id}:{r['chat_id']}")])
                nav=[]
                if page>0: nav.append(self._owner_button(self._owner_text(lang,"prev"),f"o:uw:{user_id}:{page-1}"))
                if page+1<pages: nav.append(self._owner_button(self._owner_text(lang,"next"),f"o:uw:{user_id}:{page+1}"))
                if nav: rows.append(nav)
                rows.append([self._owner_button(self._owner_text(lang,"user_reset_warnings"),f"o:urw:{user_id}")])
                rows.append([self._owner_button("◀️ کاربر",f"o:u:{user_id}")])
                text=f"⚠️ <b>{self._owner_text(lang,'user_warnings')}</b>\nUser: <code>{user_id}</code>\nPage {page+1}/{pages} · Total groups {total}\n\n"+('\\n'.join(lines) if lines else '—')
                text=text.replace('\\n','\n')
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_user_exemptions_page(self, callback:dict[str,Any], user_id:int, page:int=0)->None:
                uid=int((callback.get("from") or {}).get("id",0)); lang=await self._owner_lang(uid); rows_data,total=await self.db.list_user_exemptions(user_id,page,6); pages=max(1,(total+5)//6); page=max(0,min(page,pages-1)); rows_data,_=await self.db.list_user_exemptions(user_id,page,6)
                lines=[]; rows=[]
                for r in rows_data:
                    title=esc(r.get('title') or 'Untitled'); lines.append(f"• <b>{title}</b> · <code>{r['chat_id']}</code> · added {esc(r.get('added_at') or '—')} · {'🟢' if r.get('bot_in_chat') else '🔴'}")
                    rows.append([self._owner_button(f"🗑 حذف معافیت {title[:18]}",f"o:uer:{user_id}:{r['chat_id']}")])
                nav=[]
                if page>0: nav.append(self._owner_button(self._owner_text(lang,"prev"),f"o:ue:{user_id}:{page-1}"))
                if page+1<pages: nav.append(self._owner_button(self._owner_text(lang,"next"),f"o:ue:{user_id}:{page+1}"))
                if nav: rows.append(nav)
                rows.append([self._owner_button("◀️ کاربر",f"o:u:{user_id}")])
                text=f"🆓 <b>{self._owner_text(lang,'user_exemptions')}</b>\nUser: <code>{user_id}</code>\nPage {page+1}/{pages} · Total {total}\n\n"+('\\n'.join(lines) if lines else '—')
                text=text.replace('\\n','\n')
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_user_activity_page(self, callback:dict[str,Any], user_id:int, page:int=0)->None:
                uid=int((callback.get("from") or {}).get("id",0)); lang=await self._owner_lang(uid); logs,total=await self.db.list_user_audit_logs(user_id,page,6); pages=max(1,(total+5)//6); page=max(0,min(page,pages-1)); logs,_=await self.db.list_user_audit_logs(user_id,page,6)
                lines=[]
                for a in logs:
                    lines.append(f"• <b>{esc(a.get('event_type') or 'event')}</b> · {esc(a.get('created_at') or '—')}\n  chat=<code>{a.get('chat_id') or '—'}</code> actor=<code>{a.get('actor_id') or '—'}</code>\n  {esc(a.get('details') or '')[:300]}")
                nav=[]
                if page>0: nav.append(self._owner_button(self._owner_text(lang,"prev"),f"o:ua:{user_id}:{page-1}"))
                if page+1<pages: nav.append(self._owner_button(self._owner_text(lang,"next"),f"o:ua:{user_id}:{page+1}"))
                rows=[nav] if nav else []
                rows.append([self._owner_button("◀️ کاربر",f"o:u:{user_id}")])
                text=f"📝 <b>{self._owner_text(lang,'user_activity')}</b>\nUser: <code>{user_id}</code>\nPage {page+1}/{pages} · Total {total}\n\n"+('\\n'.join(lines) if lines else '—')
                text=text.replace('\\n','\n')
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_user_language_page(self, callback:dict[str,Any], user_id:int)->None:
                uid=int((callback.get("from") or {}).get("id",0)); lang=await self._owner_lang(uid); rows=[]
                for code,info in LANGUAGES.items():
                    rows.append([self._owner_button(f"{info['flag']} {info['name']}",f"o:usl:{user_id}:{code}")])
                rows.append([self._owner_button("◀️ کاربر",f"o:u:{user_id}")])
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,"🌐 <b>انتخاب زبان کاربر</b>",{"inline_keyboard":rows})

            async def _owner_audit_page(self, callback: dict[str, Any], page:int=0, chat_id:Optional[int]=None) -> None:
                uid=int((callback.get("from") or {}).get("id",0)); lang=await self._owner_lang(uid); logs,total=await self.db.list_audit_logs(chat_id,page,8); pages=max(1,(total+7)//8); page=max(0,min(page,pages-1)); logs,_=await self.db.list_audit_logs(chat_id,page,8)
                lines=[]
                for a in logs:
                    lines.append(f"• <b>{esc(a.get('event_type'))}</b> · {esc(a.get('created_at'))}\n  chat=<code>{a.get('chat_id') or '—'}</code> actor=<code>{a.get('actor_id') or '—'}</code>\n  {esc(a.get('details') or '')[:260]}")
                nav=[]
                if page>0: nav.append(self._owner_button("⬅️",f"o:audit:{page-1}"))
                if page+1<pages: nav.append(self._owner_button("➡️",f"o:audit:{page+1}"))
                rows=[nav] if nav else []
                rows.append([self._owner_button("◀️ بازگشت","o:home")])
                text=f"{self._owner_text(lang,'title')}\n\n📝 <b>Audit logs</b>\nPage {page+1}/{pages} · Total {total}\n\n"+('\n'.join(lines) if lines else '—')
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_period_page(self, callback: dict[str,Any]) -> None:
                uid=int((callback.get("from") or {}).get("id",0)); lang=await self._owner_lang(uid)
                d1=await self.db.period_stats(1); d7=await self.db.period_stats(7); d30=await self.db.period_stats(30)
                text=(f"{self._owner_text(lang,'title')}\n\n📈 <b>آمار زمانی</b>\n\n"
                      f"<b>امروز</b> · Checked {d1['checked']} · NSFW {d1['nsfw']} · Actions {d1['actions']} · Deleted {d1['deleted']}\n"
                      f"<b>۷ روز</b> · Checked {d7['checked']} · NSFW {d7['nsfw']} · Actions {d7['actions']} · Deleted {d7['deleted']}\n"
                      f"<b>۳۰ روز</b> · Checked {d30['checked']} · NSFW {d30['nsfw']} · Actions {d30['actions']} · Deleted {d30['deleted']}")
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":[[self._owner_button("◀️ بازگشت","o:home")]]})

            async def _owner_broadcast_page(self, callback: dict[str, Any]) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid): await self.api.answer_callback(callback["id"],"Owner only"); return
                lang=await self._owner_lang(uid)
                rows=[
                    [self._owner_button(self._owner_text(lang,"broadcast_groups"),"o:bc:g")],
                    [self._owner_button(self._owner_text(lang,"broadcast_users"),"o:bc:u")],
                    [self._owner_button(self._owner_text(lang,"back"),"o:home")],
                ]
                await self.api.answer_callback(callback["id"])
                await self._owner_edit(callback,f"{self._owner_text(lang,'title')}\n\n📣 <b>{self._owner_text(lang,'broadcast')}</b>\n\nSupports text and media.",{"inline_keyboard":rows})

            async def _owner_system_page(self, callback: dict[str, Any]) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid): await self.api.answer_callback(callback["id"],"Owner only"); return
                lang=await self._owner_lang(uid)
                stats=await self.db.owner_stats()
                text=(f"{self._owner_text(lang,'title')}\n\n🧠 <b>{self._owner_text(lang,'system')}</b>\n"
                      f"• Python: <b>{esc(platform.python_version())}</b> · PID <code>{os.getpid()}</code>\n"
                      f"• OS: <b>{esc(platform.system())} {esc(platform.release())}</b>\n"
                      f"• CPU cores: <b>{os.cpu_count() or 1}</b>\n"
                      f"• RSS: <b>{int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024) if os.name != 'nt' else int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)}</b> MB\n"
                      f"• Model: <code>{esc(self.detector.model_id)}</code>\n"
                      f"• Detector signature: <code>{esc(self.detector.signature)}</code>\n"
                      f"• Device: <b>{esc(str(self.detector.device))}</b>\n"
                      f"• Cache entries: <b>{len(self.memory_cache)}</b>\n"
                      f"• In-flight detections: <b>{len(self.inflight)}</b>\n"
                      f"• DB groups: <b>{stats['groups']}</b>\n"
                      f"• DB users: <b>{stats['users']}</b>\n"
                      f"• Database groups: <b>{stats['groups']}</b>")
                rows=[[self._owner_button(self._owner_text(lang,"back"),"o:home")]]
                await self.api.answer_callback(callback["id"])
                await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_group_snapshot(self, chat_id: int) -> dict[str, Any]:
                dbgroup=await self.db.get_chat(chat_id) or {}
                info={}; count=None; admins=[]; bot_member=None; errors=[]
                try: info=await self.api.get_chat(chat_id) or {}
                except Exception as exc: errors.append(f"getChat: {exc}")
                try: count=await self.api.get_chat_member_count(chat_id)
                except Exception as exc: errors.append(f"memberCount: {exc}")
                try: admins=await self.api.get_chat_administrators(chat_id)
                except Exception as exc: errors.append(f"admins: {exc}")
                try: bot_member=await self.api.get_chat_member(chat_id,self.bot_id)
                except Exception as exc: errors.append(f"botMember: {exc}")
                return {"db":dbgroup,"info":info,"count":count,"admins":admins,"bot_member":bot_member,"errors":errors}

            async def _owner_group_detail(self, callback: dict[str, Any], chat_id: int) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid): await self.api.answer_callback(callback["id"],"Owner only"); return
                lang=await self._owner_lang(uid); snap=await self._owner_group_snapshot(chat_id)
                dbg=snap["db"]; info=snap["info"]; count=snap["count"]; botm=snap["bot_member"] or {}
                username=info.get("username")
                public_link=f"https://t.me/{username}" if username else None
                desc=info.get("description") or "—"
                if len(desc)>700: desc=desc[:697]+"…"
                perms=botm.get("can_delete_messages") if isinstance(botm,dict) else None
                stats=await self.db.get_chat_stats(chat_id)
                tracked=await self.db.tracked_chat_user_count(chat_id)
                member_state=botm.get("status") if isinstance(botm,dict) else None
                state="🟢" if dbg.get("enabled") else "🔴"
                permission_keys=[
                    "can_delete_messages","can_restrict_members","can_change_info","can_invite_users","can_pin_messages",
                    "can_manage_video_chats","can_promote_members","can_manage_topics","can_manage_voice_chats",
                    "can_post_messages","can_edit_messages","can_delete_sent_messages","can_post_stories","can_edit_stories","can_delete_stories",
                ]
                perm_lines=[]
                for key in permission_keys:
                    if key in botm:
                        perm_lines.append(f"{key.replace('can_','').replace('_',' ')}={'✅' if botm.get(key) else '❌'}")
                perm_text=' · '.join(perm_lines) if perm_lines else '—'
                text=(f"{self._owner_text(lang,'title')}\n\n📋 <b>{esc(info.get('title') or dbg.get('title') or 'Untitled')}</b>\n"
                      f"<code>{chat_id}</code>\n\n"
                      f"• Type: <b>{esc(info.get('type') or dbg.get('chat_type') or 'unknown')}</b>\n"
                      f"• Members: <b>{count if count is not None else '—'}</b>\n"
                      f"• Username: <b>{('@'+esc(username)) if username else '—'}</b>\n"
                      f"• Public link: {f'<a href=\"{public_link}\">{esc(public_link)}</a>' if public_link else '—'}\n"
                      f"• Invite link: {f'<a href=\"{esc(info.get("invite_link"))}\">open invite</a>' if info.get('invite_link') else '—'}\n"
                      f"• Forum: <b>{'yes' if info.get('is_forum') else 'no'}</b> · Hidden members: <b>{'yes' if info.get('has_hidden_members') else 'no'}</b>\n"
                      f"• Slow mode: <b>{info.get('slow_mode_delay',0) or 0}s</b> · Auto-delete: <b>{info.get('message_auto_delete_time',0) or 0}s</b>\n"
                      f"• Protected content: <b>{'yes' if info.get('has_protected_content') else 'no'}</b> · Join request: <b>{'yes' if info.get('join_by_request') else 'no'}</b>\n"
                      f"• Bot status: <b>{esc(member_state or 'unknown')}</b>\n"
                      f"• Delete messages: <b>{'yes' if botm.get('can_delete_messages') else 'no/unknown'}</b> · Restrict: <b>{'yes' if botm.get('can_restrict_members') else 'no/unknown'}</b>\n"
                      f"• Change info: <b>{'yes' if botm.get('can_change_info') else 'no/unknown'}</b> · Invite: <b>{'yes' if botm.get('can_invite_users') else 'no/unknown'}</b>\n"
                      f"• Permissions: <b>{esc(perm_text)}</b>\n"
                      f"• Protection: {state}\n"
                      f"• Admin moderation: <b>{'ON' if dbg.get('moderate_admins') else 'OFF'}</b>\n"
                      f"• Threshold: <b>{float(dbg.get('threshold',DEFAULT_THRESHOLD)):.0%}</b>\n"
                      f"• Action: <b>{esc(dbg.get('action') or 'delete')}</b>\n\n"
                      f"<b>Stats</b>: checked {stats['checked']} · NSFW {stats['nsfw']} · actions {stats['actions']} · deleted {stats['deleted']}\n"
                      f"Tracked users: <b>{tracked}</b>\n\n"
                      f"<b>Description</b>\n{esc(desc)}")
                rows=[
                    [self._owner_button(self._owner_text(lang,"group_info"),f"o:gi:{chat_id}"),self._owner_button(self._owner_text(lang,"group_stats"),f"o:gs:{chat_id}")],
                    [self._owner_button(self._owner_text(lang,"group_admins"),f"o:ga:{chat_id}:0"),self._owner_button(self._owner_text(lang,"group_members"),f"o:gm:{chat_id}:0")],
                    [self._owner_button(self._owner_text(lang,"exempt"),f"o:ge:{chat_id}:0"),self._owner_button(self._owner_text(lang,"blocked"),f"o:gb:{chat_id}:0")],
                    [self._owner_button(self._owner_text(lang,"group_audit"),f"o:gx:{chat_id}:0"),self._owner_button(self._owner_text(lang,"group_settings"),f"o:gcfg:{chat_id}")],
                    [self._owner_button(self._owner_text(lang,"send_group"),f"o:send:{chat_id}")],
                    [self._owner_button("🚪 Leave group",f"o:leaveask:{chat_id}"),self._owner_button(self._owner_text(lang,"refresh"),f"o:g:{chat_id}")],
                    [self._owner_button(self._owner_text(lang,"groups"),"o:groups:0")],
                    [self._owner_button(self._owner_text(lang,"back"),"o:groups:0")],
                ]
                if public_link:
                    rows.insert(3,[{"text":"🔗 Open public link","url":public_link}])
                await self.api.answer_callback(callback["id"])
                await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_group_admins(self, callback: dict[str, Any], chat_id: int, page: int=0) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid): await self.api.answer_callback(callback["id"],"Owner only"); return
                lang=await self._owner_lang(uid)
                admins=await self.api.get_chat_administrators(chat_id)
                per_page=5; total=max(1,(len(admins)+per_page-1)//per_page); page=max(0,min(page,total-1)); chunk=admins[page*per_page:(page+1)*per_page]
                lines=[]
                for a in chunk:
                    u=a.get("user") or {}; name=esc((u.get("first_name") or "User")+((" "+u.get("last_name")) if u.get("last_name") else "")); uname=(" @"+esc(u["username"])) if u.get("username") else ""; status=esc(a.get("status") or ""); title=esc(a.get("custom_title") or "")
                    lines.append(f"• <b>{name}</b>{uname}\n  <code>{u.get('id')}</code> · {status}" + (f" · {title}" if title else ""))
                text=(f"{self._owner_text(lang,'title')}\n\n👮 <b>{self._owner_text(lang,'group_admins')}</b>\n"
                      f"Group: <code>{chat_id}</code>\nPage {page+1}/{total}\n\n"+("\n".join(lines) if lines else "—")+f"\n\n{self._owner_text(lang,'admin_note')}")
                nav=[]
                if page>0: nav.append(self._owner_button(self._owner_text(lang,"prev"),f"o:ga:{chat_id}:{page-1}"))
                if page+1<total: nav.append(self._owner_button(self._owner_text(lang,"next"),f"o:ga:{chat_id}:{page+1}"))
                rows=[]
                if nav: rows.append(nav)
                rows.append([self._owner_button(self._owner_text(lang,"back"),f"o:g:{chat_id}")])
                await self.api.answer_callback(callback["id"])
                await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_group_members(self, callback: dict[str, Any], chat_id: int, page: int=0) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid): await self.api.answer_callback(callback["id"],"Owner only"); return
                lang=await self._owner_lang(uid); total=await self.db.tracked_chat_user_count(chat_id); pages=max(1,(total+7)//8); page=max(0,min(page,pages-1)); rows_users=await self.db.list_tracked_chat_users(chat_id,page,8)
                lines=[]
                for u in rows_users:
                    name=esc((u.get("first_name") or "User")+((" "+u.get("last_name")) if u.get("last_name") else "")); uname=(" @"+esc(u["username"])) if u.get("username") else ""; lines.append(f"• <b>{name}</b>{uname}\n  <code>{u['user_id']}</code> · msgs {u['message_count']} · {esc(u['last_seen'])}")
                text=(f"{self._owner_text(lang,'title')}\n\n👥 <b>{self._owner_text(lang,'group_members')}</b>\nGroup: <code>{chat_id}</code>\nPage {page+1}/{pages}\n\n"+("\n".join(lines) if lines else "—")+f"\n\n{self._owner_text(lang,'members_note')}")
                nav=[]
                if page>0: nav.append(self._owner_button(self._owner_text(lang,"prev"),f"o:gm:{chat_id}:{page-1}"))
                if page+1<pages: nav.append(self._owner_button(self._owner_text(lang,"next"),f"o:gm:{chat_id}:{page+1}"))
                rows=[]
                if nav: rows.append(nav)
                rows.append([self._owner_button(self._owner_text(lang,"back"),f"o:g:{chat_id}")])
                await self.api.answer_callback(callback["id"])
                await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_group_exempt(self, callback:dict[str,Any], chat_id:int, page:int=0)->None:
                uid=int((callback.get("from") or {}).get("id",0)); lang=await self._owner_lang(uid); rows_data,total=await self.db.list_exempt_users(chat_id,page,8); pages=max(1,(total+7)//8); page=max(0,min(page,pages-1)); rows_data,_=await self.db.list_exempt_users(chat_id,page,8)
                lines=[]
                for r in rows_data:
                    name=esc(((r.get('first_name') or '')+' '+(r.get('last_name') or '')).strip() or f"User {r['user_id']}"); uname=(" @"+esc(r['username'])) if r.get('username') else ''
                    lines.append(f"• {name}{uname} · <code>{r['user_id']}</code> · added {esc(r.get('added_at') or '—')}")
                nav=[]
                if page>0: nav.append(self._owner_button("⬅️",f"o:ge:{chat_id}:{page-1}"))
                if page+1<pages: nav.append(self._owner_button("➡️",f"o:ge:{chat_id}:{page+1}"))
                rows=[nav] if nav else []; rows.append([self._owner_button("◀️ بازگشت",f"o:g:{chat_id}")])
                text=f"👥 <b>Exempt users</b>\nGroup: <code>{chat_id}</code>\nPage {page+1}/{pages}\n\n"+('\n'.join(lines) if lines else '—')
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_group_blocked(self, callback:dict[str,Any], chat_id:int, page:int=0)->None:
                uid=int((callback.get("from") or {}).get("id",0)); rows_data,total=await self.db.list_blocked_media(chat_id,page,6); pages=max(1,(total+5)//6); page=max(0,min(page,pages-1)); rows_data,_=await self.db.list_blocked_media(chat_id,page,6)
                lines=[f"• <code>{esc(r.get('media_key') or '')[:32]}</code> · {esc(r.get('kind') or 'media')} · {esc(r.get('blocked_at') or '—')}" for r in rows_data]
                nav=[]
                if page>0: nav.append(self._owner_button("⬅️",f"o:gb:{chat_id}:{page-1}"))
                if page+1<pages: nav.append(self._owner_button("➡️",f"o:gb:{chat_id}:{page+1}"))
                rows=[nav] if nav else []; rows.append([self._owner_button("◀️ بازگشت",f"o:g:{chat_id}")])
                text=f"🚫 <b>Blocked media</b>\nGroup: <code>{chat_id}</code>\nPage {page+1}/{pages}\n\n"+('\n'.join(lines) if lines else '—')
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_group_audit(self, callback:dict[str,Any], chat_id:int, page:int=0)->None:
                logs,total=await self.db.list_audit_logs(chat_id,page,8); pages=max(1,(total+7)//8); page=max(0,min(page,pages-1)); logs,_=await self.db.list_audit_logs(chat_id,page,8)
                lines=[f"• <b>{esc(a.get('event_type'))}</b> · {esc(a.get('created_at'))}\n  {esc(a.get('details') or '')[:300]}" for a in logs]
                nav=[]
                if page>0: nav.append(self._owner_button("⬅️",f"o:gx:{chat_id}:{page-1}"))
                if page+1<pages: nav.append(self._owner_button("➡️",f"o:gx:{chat_id}:{page+1}"))
                rows=[nav] if nav else []; rows.append([self._owner_button("◀️ بازگشت",f"o:g:{chat_id}")])
                text=f"📝 <b>Group audit</b>\nGroup: <code>{chat_id}</code>\nPage {page+1}/{pages}\n\n"+('\n'.join(lines) if lines else '—')
                await self.api.answer_callback(callback['id']); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_group_settings(self, callback: dict[str, Any], chat_id: int) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid): await self.api.answer_callback(callback["id"],"Owner only"); return
                lang=await self._owner_lang(uid); g=await self.db.get_chat(chat_id) or await self.db.ensure_chat(chat_id)
                rows=[
                    [self._owner_button(f"🛡 Protection: {'ON' if g['enabled'] else 'OFF'}",f"o:gset:{chat_id}:toggle"),self._owner_button(f"👮 Admins: {'ON' if g.get('moderate_admins') else 'OFF'}",f"o:gset:{chat_id}:admins")],
                    [self._owner_button("🎚 Threshold",f"o:gth:{chat_id}"),self._owner_button("🛡 Action",f"o:gac:{chat_id}")],
                    [self._owner_button("⚠️ Warn limit",f"o:gw:{chat_id}"),self._owner_button("🔇 Mute duration",f"o:gwm:{chat_id}")],
                    [self._owner_button("⛔ Escalation",f"o:ges:{chat_id}"),self._owner_button("🌐 Language",f"o:glang:{chat_id}")],
                    [self._owner_button("✏️ Custom message",f"o:gmsg:{chat_id}"),self._owner_button("🔄 Back",f"o:g:{chat_id}")],
                    [self._owner_button(self._owner_text(lang,"back"),f"o:g:{chat_id}")],
                ]
                text=(f"{self._owner_text(lang,'title')}\n\n⚙️ <b>{self._owner_text(lang,'group_settings')}</b>\nGroup: <code>{chat_id}</code>\n\n"
                      f"Protection: <b>{'ON' if g['enabled'] else 'OFF'}</b>\n"
                      f"Admin moderation: <b>{'ON' if g.get('moderate_admins') else 'OFF'}</b>\n"
                      f"Threshold: <b>{float(g.get('threshold',DEFAULT_THRESHOLD)):.0%}</b>\n"
                      f"Action: <b>{esc(g.get('action') or 'delete')}</b>\n"
                      f"Warn limit: <b>{g.get('warn_limit')}</b>\n"
                      f"Escalation: <b>{esc(g.get('escalation') or 'none')}</b>\n"
                      f"Mute: <b>{g.get('mute_minutes')} min</b>\n"
                      f"Language: <b>{esc(g.get('language') or DEFAULT_LANGUAGE)}</b>")
                await self.api.answer_callback(callback["id"]); await self._owner_edit(callback,text,{"inline_keyboard":rows})

            async def _owner_group_stats(self, callback: dict[str, Any], chat_id: int) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid): await self.api.answer_callback(callback["id"],"Owner only"); return
                lang=await self._owner_lang(uid); st=await self.db.get_chat_stats(chat_id); g=await self.db.get_chat(chat_id) or {}; snap=await self._owner_group_snapshot(chat_id)
                text=(f"{self._owner_text(lang,'title')}\n\n📊 <b>{self._owner_text(lang,'group_stats')}</b>\nGroup: <code>{chat_id}</code>\n\n"
                      f"Checked: <b>{st['checked']}</b>\nNSFW: <b>{st['nsfw']}</b>\nActions: <b>{st['actions']}</b>\nDeleted: <b>{st['deleted']}</b>\n"
                      f"Exempt: <b>{await self.db.exempt_count(chat_id)}</b>\nBlocked media: <b>{await self.db.blocked_count(chat_id)}</b>\nTracked users: <b>{await self.db.tracked_chat_user_count(chat_id)}</b>\n"
                      f"Members now: <b>{snap['count'] if snap['count'] is not None else '—'}</b>\nUpdated: <b>{esc(str(g.get('updated_at') or '—'))}</b>")
                await self.api.answer_callback(callback["id"]); await self._owner_edit(callback,text,{"inline_keyboard":[[self._owner_button(self._owner_text(lang,"refresh"),f"o:gs:{chat_id}")],[self._owner_button(self._owner_text(lang,"back"),f"o:g:{chat_id}")]]})

            async def _owner_send_group(self, callback: dict[str, Any], chat_id: int) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid): await self.api.answer_callback(callback["id"],"Owner only"); return
                lang=await self._owner_lang(uid); self.owner_pending[uid]={"mode":"send_one","target":chat_id}
                await self.api.answer_callback(callback["id"],self._owner_text(lang,"prompt_send"))
                await self.api.send_message(uid,self._owner_text(lang,"prompt_send"),reply_markup={"inline_keyboard":[[self._owner_button(self._owner_text(lang,"cancel"),"o:cancel")]]},parse_mode="HTML")

            async def _owner_begin_broadcast(self, callback: dict[str, Any], users: bool) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid): await self.api.answer_callback(callback["id"],"Owner only"); return
                lang=await self._owner_lang(uid); self.owner_pending[uid]={"mode":"broadcast_users" if users else "broadcast_groups"}
                key="prompt_broadcast_users" if users else "prompt_broadcast_groups"
                await self.api.answer_callback(callback["id"],self._owner_text(lang,key))
                await self.api.send_message(uid,self._owner_text(lang,key),reply_markup={"inline_keyboard":[[self._owner_button(self._owner_text(lang,"cancel"),"o:cancel")]]})

            async def handle_owner_pending(self,message:dict[str,Any])->bool:
                uid=int(message.get("from",{}).get("id",0))
                if uid!=OWNER_ID or message.get("chat",{}).get("type")!="private": return False
                pending=self.owner_pending.get(uid)
                if not pending: return False
                mode=pending.get("mode")
                if mode == "group_message":
                    target=int(pending.get("target")); text=message.get("text") or message.get("caption") or ""
                    if not text:
                        await self.api.send_message(uid,"⚠️ پیام متنی بفرست."); return True
                    await self.db.set_chat(target,custom_message=text[:900]); await self.db.audit("owner_custom_message",target,uid,details="custom moderation message updated")
                    self.owner_pending.pop(uid,None); await self.api.send_message(uid,"✅ پیام moderation ذخیره شد.",reply_markup=self._owner_main_keyboard(await self._owner_lang(uid))); return True
                if mode == "user_note":
                    target=int(pending.get("target")); note=(message.get("text") or message.get("caption") or "").strip()
                    if not note:
                        await self.api.send_message(uid,"⚠️ متن یادداشت را بفرست."); return True
                    await self.db.set_user_note(target,note)
                    await self.db.audit("owner_user_note",None,uid,details=f"user_id={target} note_updated=1")
                    self.owner_pending.pop(uid,None)
                    await self.api.send_message(uid,"✅ یادداشت کاربر ذخیره شد.",reply_markup=self._owner_main_keyboard(await self._owner_lang(uid)))
                    return True
                if mode == "search_user":
                    raw=(message.get("text") or "").strip()
                    if not raw:
                        await self.api.send_message(uid,self._owner_text(await self._owner_lang(uid),"prompt_user_search")); return True
                    users,total=await self.db.list_users(0,10,raw)
                    rows=[]
                    for u in users:
                        label=((u.get("first_name") or "")+((" "+u.get("last_name")) if u.get("last_name") else "")).strip() or f"User {u['user_id']}"
                        rows.append([self._owner_button(f"👤 {label[:34]}",f"o:u:{u['user_id']}")])
                    rows.append([self._owner_button(self._owner_text(await self._owner_lang(uid),"back"),"o:home")])
                    await self.api.send_message(uid,f"🔎 <b>{esc(raw)}</b> · {total} result(s)",parse_mode="HTML",reply_markup={"inline_keyboard":rows})
                    self.owner_pending.pop(uid,None)
                    return True
                if mode == "detection_test":
                    media=media_from_message(message)
                    if not media:
                        await self.api.send_message(uid,"⚠️ Please send supported image/video/sticker/GIF/TGS media, or cancel the test.")
                        return True
                    try:
                        confidence=await self._detect_media_once(media)
                        await self.api.send_message(uid, f"🧪 <b>Detection test</b>\nType: <code>{esc(media.kind)}</code>\nConfidence: <b>{confidence:.1%}</b>\nThreshold examples: 10% → 100%", parse_mode="HTML", reply_markup=self._owner_main_keyboard(await self._owner_lang(uid)))
                    except Exception as exc:
                        logging.exception("OWNER_TEST_FAILED error=%s", exc)
                        await self.api.send_message(uid, f"⚠️ Detection test failed: <code>{esc(type(exc).__name__)}</code>", parse_mode="HTML")
                    self.owner_pending.pop(uid,None)
                    return True
                self.owner_pending.pop(uid,None)
                targets=[]
                if mode=="send_one": targets=[int(pending["target"])]
                elif mode=="broadcast_groups": targets=[int(g["chat_id"]) for g in await self.db.list_active_groups()]
                elif mode=="broadcast_users": targets=await self.db.list_started_user_ids()
                elif mode=="search_group":
                    raw=(message.get("text") or "").strip()
                    if raw.startswith("https://t.me/"): raw="@"+raw.rsplit("/",1)[-1]
                    try:
                        lookup: int | str = int(raw) if re.fullmatch(r"-?\d+", raw) else raw
                        apiinfo=await self.api.get_chat(lookup)
                        gid=int(apiinfo.get("id"))
                        await self.db.ensure_chat(gid,apiinfo.get("title", ""),apiinfo.get("type", "supergroup"))
                        text=f"🔎 <b>{esc(apiinfo.get('title') or 'Group')}</b>\n<code>{gid}</code>\nUsername: <b>{('@'+esc(apiinfo.get('username'))) if apiinfo.get('username') else '—'}</b>"
                        await self.api.send_message(uid,text,parse_mode="HTML",reply_markup={"inline_keyboard":[[self._owner_button("📋 Open details",f"o:g:{gid}")],[self._owner_button("🏠 Home","o:home")]]})
                    except Exception:
                        await self.api.send_message(uid,"⚠️ Group not found.")
                    return True
                if not targets:
                    await self.api.send_message(uid,"⚠️ No targets."); return True
                sent=failed=0
                for target in targets:
                    try:
                        mid=message.get("message_id")
                        if mid:
                            await self.api.copy_message(target,uid,int(mid))
                        elif message.get("text"):
                            await self.api.send_message(target, message["text"])
                        else:
                            failed+=1; continue
                        sent+=1
                    except Exception as exc:
                        logging.warning("OWNER_PENDING_SEND_FAILED target=%s error=%s",target,exc); failed+=1
                    await asyncio.sleep(0.04)
                lang=await self._owner_lang(uid)
                await self.db.audit("owner_broadcast",None,uid,details=f"mode={mode} sent={sent} failed={failed}")
                await self.api.send_message(uid,self._owner_text(lang,"send_result",sent=sent,failed=failed))
                return True

            async def owner_callback(self, callback: dict[str, Any]) -> None:
                uid=int((callback.get("from") or {}).get("id",0))
                if not await self.is_owner(uid):
                    await self.api.answer_callback(callback.get("id",""),"Owner only"); return
                data=callback.get("data") or ""; parts=data.split(":")
                try:
                    if data=="o:home" or data=="o:dash": await self._owner_show_home(callback); return
                    if data.startswith("o:groups:"): await self._owner_group_list(callback,int(parts[2])); return
                    if data.startswith("o:users:"): await self._owner_users_page(callback,int(parts[2])); return
                    if data=="o:usearch":
                        lang=await self._owner_lang(uid); self.owner_pending[uid]={"mode":"search_user"}; await self.api.answer_callback(callback["id"],self._owner_text(lang,"prompt_user_search")); await self.api.send_message(uid,self._owner_text(lang,"prompt_user_search"),reply_markup={"inline_keyboard":[[self._owner_button(self._owner_text(lang,"cancel"),"o:cancel")]]}); return
                    if data.startswith("o:u:"): await self._owner_user_detail(callback,int(parts[2])); return
                    if data.startswith("o:ug:"): await self._owner_user_groups_page(callback,int(parts[2]),int(parts[3])); return
                    if data.startswith("o:uw:"): await self._owner_user_warnings_page(callback,int(parts[2]),int(parts[3])); return
                    if data.startswith("o:ue:"): await self._owner_user_exemptions_page(callback,int(parts[2]),int(parts[3])); return
                    if data.startswith("o:ua:"): await self._owner_user_activity_page(callback,int(parts[2]),int(parts[3])); return
                    if data.startswith("o:ul:"): await self._owner_user_language_page(callback,int(parts[2])); return
                    if data.startswith("o:usl:"):
                        target=int(parts[2]); code=parts[3]
                        if code in LANGUAGES:
                            await self.db.upsert_user(target,language=code)
                            await self.db.audit("owner_user_language",None,uid,details=f"user_id={target} language={code}")
                        await self._owner_user_detail(callback,target); return
                    if data.startswith("o:ub:"):
                        target=int(parts[2]); blocked=not await self.db.is_user_blocked(target)
                        await self.db.set_user_blocked(target,blocked); await self.db.audit("owner_user_block" if blocked else "owner_user_unblock",None,uid,details=f"user_id={target}")
                        await self.api.answer_callback(callback["id"],"OK"); await self._owner_user_detail(callback,target); return
                    if data.startswith("o:urw:"):
                        target=int(parts[2]); lang=await self._owner_lang(uid); await self.api.answer_callback(callback["id"]); await self._owner_edit(callback,self._owner_text(lang,"user_reset_confirm"),{"inline_keyboard":[[self._owner_button("✅ تأیید","o:urwy:"+str(target)),self._owner_button("❌ لغو",f"o:u:{target}")]]}); return
                    if data.startswith("o:urwy:"):
                        target=int(parts[2]); n=await self.db.reset_user_warnings(target); await self.db.audit("owner_user_reset_warnings",None,uid,details=f"user_id={target} deleted={n}"); await self.api.answer_callback(callback["id"],"OK"); await self._owner_user_detail(callback,target); return
                    if data.startswith("o:uwr:"):
                        target=int(parts[2]); cid=int(parts[3]); n=await self.db.reset_user_warnings(target,cid); await self.db.audit("owner_user_reset_group_warnings",cid,uid,details=f"user_id={target} deleted={n}"); await self.api.answer_callback(callback["id"],"OK"); await self._owner_user_warnings_page(callback,target,0); return
                    if data.startswith("o:uer:"):
                        target=int(parts[2]); cid=int(parts[3]); await self.db.remove_exempt_user(cid,target); await self.db.audit("owner_user_unexempt",cid,uid,details=f"user_id={target}"); await self.api.answer_callback(callback["id"],"OK"); await self._owner_user_exemptions_page(callback,target,0); return
                    if data.startswith("o:un:"):
                        target=int(parts[2]); lang=await self._owner_lang(uid); self.owner_pending[uid]={"mode":"user_note","target":target}; await self.api.answer_callback(callback["id"]); await self.api.send_message(uid,self._owner_text(lang,"prompt_user_note"),reply_markup={"inline_keyboard":[[self._owner_button(self._owner_text(lang,"cancel"),"o:cancel")]]}); return
                    if data.startswith("o:usend:"):
                        target=int(parts[2]); lang=await self._owner_lang(uid); self.owner_pending[uid]={"mode":"send_one","target":target}; await self.api.answer_callback(callback["id"]); await self.api.send_message(uid,self._owner_text(lang,"prompt_user_send"),reply_markup={"inline_keyboard":[[self._owner_button(self._owner_text(lang,"cancel"),"o:cancel")]]},parse_mode="HTML"); return
                    if data.startswith("o:audit:"): await self._owner_audit_page(callback,int(parts[2])); return
                    if data=="o:period": await self._owner_period_page(callback); return
                    if data=="o:test":
                        lang=await self._owner_lang(uid); self.owner_pending[uid]={"mode":"detection_test"}; await self.api.answer_callback(callback["id"],self._owner_text(lang,"prompt_test")); await self.api.send_message(uid,self._owner_text(lang,"prompt_test"),reply_markup={"inline_keyboard":[[self._owner_button(self._owner_text(lang,"prompt_test_cancel"),"o:cancel")]]}); return
                    if data=="o:broadcast": await self._owner_broadcast_page(callback); return
                    if data=="o:system": await self._owner_system_page(callback); return
                    if data=="o:search":
                        lang=await self._owner_lang(uid); self.owner_pending[uid]={"mode":"search_group"}; await self.api.answer_callback(callback["id"],self._owner_text(lang,"prompt_group_search")); await self.api.send_message(uid,self._owner_text(lang,"prompt_group_search"),reply_markup={"inline_keyboard":[[self._owner_button(self._owner_text(lang,"cancel"),"o:cancel")]]}); return
                    if data=="o:cancel":
                        self.owner_pending.pop(uid,None); lang=await self._owner_lang(uid); await self.api.answer_callback(callback["id"]); await self.api.send_message(uid,self._owner_text(lang,"cancelled"),reply_markup=self._owner_main_keyboard(lang)); return
                    if data=="o:bc:g": await self._owner_begin_broadcast(callback,False); return
                    if data=="o:bc:u": await self._owner_begin_broadcast(callback,True); return
                    if data.startswith("o:g:"): await self._owner_group_detail(callback,int(parts[2])); return
                    if data.startswith("o:gi:"):
                        await self._owner_group_detail(callback,int(parts[2])); return
                    if data.startswith("o:gs:"): await self._owner_group_stats(callback,int(parts[2])); return
                    if data.startswith("o:ga:"): await self._owner_group_admins(callback,int(parts[2]),int(parts[3])); return
                    if data.startswith("o:gm:"): await self._owner_group_members(callback,int(parts[2]),int(parts[3])); return
                    if data.startswith("o:ge:"): await self._owner_group_exempt(callback,int(parts[2]),int(parts[3])); return
                    if data.startswith("o:gb:"): await self._owner_group_blocked(callback,int(parts[2]),int(parts[3])); return
                    if data.startswith("o:gx:"): await self._owner_group_audit(callback,int(parts[2]),int(parts[3])); return
                    if data.startswith("o:gcfg:"): await self._owner_group_settings(callback,int(parts[2])); return
                    if data.startswith("o:send:"): await self._owner_send_group(callback,int(parts[2])); return
                    if data.startswith("o:leaveask:"):
                        cid=int(parts[2]); lang=await self._owner_lang(uid); await self.api.answer_callback(callback["id"]); await self._owner_edit(callback, f"⚠️ <b>Leave group?</b>\n<code>{cid}</code>\n\nThis removes the bot from the group.", {"inline_keyboard":[[self._owner_button("✅ Confirm",f"o:leave:{cid}:yes"),self._owner_button("❌ Cancel",f"o:g:{cid}")]]}); return
                    if data.startswith("o:leave:"):
                        cid=int(parts[2]); await self.api.answer_callback(callback["id"]);
                        if len(parts)>3 and parts[3]=="yes":
                            try:
                                await self.api.call("leaveChat",{"chat_id":cid})
                                await self.db.mark_chat_membership(cid,False)
                                await self.db.audit("owner_leave_group",cid,uid,details="bot left group")
                                await self.api.send_message(uid,"✅ Bot left the group.")
                                lang=await self._owner_lang(uid); await self.api.send_message(uid,await self._owner_dashboard_text(lang),parse_mode="HTML",reply_markup=self._owner_main_keyboard(lang))
                            except Exception as exc:
                                logging.warning("OWNER_LEAVE_FAILED chat=%s error=%s",cid,exc); await self.api.send_message(uid,"⚠️ Could not leave this group.")
                        return
                    if data.startswith("o:gset:"):
                        cid=int(parts[2]); action=parts[3]; g=await self.db.get_chat(cid) or await self.db.ensure_chat(cid)
                        if action=="toggle": await self.db.set_chat(cid,enabled=0 if g["enabled"] else 1); await self.db.audit("owner_group_toggle",cid,uid,details=f"enabled={0 if g['enabled'] else 1}")
                        elif action=="admins": await self.db.set_chat(cid,moderate_admins=0 if g.get("moderate_admins") else 1); await self.db.audit("owner_admin_moderation",cid,uid,details=f"enabled={0 if g.get('moderate_admins') else 1}")
                        await self.api.answer_callback(callback["id"],"OK"); await self._owner_group_settings(callback,cid); return
                    if data.startswith("o:gth:"):
                        cid=int(parts[2]); lang=await self._owner_lang(uid); vals=list(THRESHOLDS); rows=[[self._owner_button(f"{v:.0%}",f"o:gsetth:{cid}:{v:.2f}") for v in vals[i:i+5]] for i in range(0,len(vals),5)]; rows.append([self._owner_button(self._owner_text(lang,"back"),f"o:gcfg:{cid}")]); await self.api.answer_callback(callback["id"]); await self._owner_edit(callback,"🎚 <b>Threshold 10% → 100%</b>",{"inline_keyboard":rows}); return
                    if data.startswith("o:gsetth:"):
                        cid=int(parts[2]); v=float(parts[3]);
                        if v in THRESHOLDS: await self.db.set_chat(cid,threshold=v); await self.db.audit("owner_threshold",cid,uid,details=f"threshold={v:.2f}")
                        await self._owner_group_settings(callback,cid); return
                    if data.startswith("o:gac:"):
                        cid=int(parts[2]); lang=await self._owner_lang(uid); rows=[[self._owner_button(str(a),f"o:gsetac:{cid}:{a}")] for a in ACTIONS]; rows.append([self._owner_button(self._owner_text(lang,"back"),f"o:gcfg:{cid}")]); await self.api.answer_callback(callback["id"]); await self._owner_edit(callback,"🛡 <b>Action</b>",{"inline_keyboard":rows}); return
                    if data.startswith("o:gsetac:"):
                        cid=int(parts[2]); a=parts[3];
                        if a in ACTIONS: await self.db.set_chat(cid,action=a); await self.db.audit("owner_action",cid,uid,details=f"action={a}")
                        await self._owner_group_settings(callback,cid); return
                    if data.startswith("o:gw:"):
                        cid=int(parts[2]); lang=await self._owner_lang(uid); rows=[[self._owner_button(str(v),f"o:gsetw:{cid}:{v}") for v in WARN_LIMITS],[self._owner_button("◀️",f"o:gcfg:{cid}")]]; await self.api.answer_callback(callback["id"]); await self._owner_edit(callback,"⚠️ <b>Warn limit</b>",{"inline_keyboard":rows}); return
                    if data.startswith("o:gsetw:"):
                        cid=int(parts[2]); v=int(parts[3]);
                        if v in WARN_LIMITS: await self.db.set_chat(cid,warn_limit=v); await self.db.audit("owner_warn_limit",cid,uid,details=f"warn_limit={v}")
                        await self._owner_group_settings(callback,cid); return
                    if data.startswith("o:gwm:"):
                        cid=int(parts[2]); rows=[[self._owner_button(f"{v}m",f"o:gsetwm:{cid}:{v}") for v in MUTE_DURATIONS[:3]],[self._owner_button(f"{v}m",f"o:gsetwm:{cid}:{v}") for v in MUTE_DURATIONS[3:]],[self._owner_button("◀️",f"o:gcfg:{cid}")]]; await self.api.answer_callback(callback["id"]); await self._owner_edit(callback,"🔇 <b>Mute duration</b>",{"inline_keyboard":rows}); return
                    if data.startswith("o:gsetwm:"):
                        cid=int(parts[2]); v=int(parts[3]);
                        if v in MUTE_DURATIONS: await self.db.set_chat(cid,mute_minutes=v); await self.db.audit("owner_mute_duration",cid,uid,details=f"minutes={v}")
                        await self._owner_group_settings(callback,cid); return
                    if data.startswith("o:gmsg:"):
                        cid=int(parts[2]); self.owner_pending[uid]={"mode":"group_message","target":cid}; lang=await self._owner_lang(uid); await self.api.answer_callback(callback["id"],"Send message"); await self.api.send_message(uid,"✏️ پیام جدید moderation را بفرست. برای لغو /start نزن؛ از دکمه لغو استفاده کن.",reply_markup={"inline_keyboard":[[self._owner_button("❌ لغو","o:cancel")]]}); return
                    if data.startswith("o:ges:"):
                        cid=int(parts[2]); lang=await self._owner_lang(uid); rows=[[self._owner_button(str(e),f"o:gsetes:{cid}:{e}")] for e in ESCALATIONS]; rows.append([self._owner_button(self._owner_text(lang,"back"),f"o:gcfg:{cid}")]); await self.api.answer_callback(callback["id"]); await self._owner_edit(callback,"⚠️ <b>Escalation</b>",{"inline_keyboard":rows}); return
                    if data.startswith("o:gsetes:"):
                        cid=int(parts[2]); e=parts[3];
                        if e in ESCALATIONS: await self.db.set_chat(cid,escalation=e); await self.db.audit("owner_escalation",cid,uid,details=f"escalation={e}")
                        await self._owner_group_settings(callback,cid); return
                    if data.startswith("o:glang:"):
                        cid=int(parts[2]); lang=await self._owner_lang(uid); rows=[[self._owner_button(f"{info['flag']} {info['name']}",f"o:gsetlang:{cid}:{code}")] for code,info in LANGUAGES.items()]; rows.append([self._owner_button(self._owner_text(lang,"back"),f"o:gcfg:{cid}")]); await self.api.answer_callback(callback["id"]); await self._owner_edit(callback,"🌐 <b>Language</b>",{"inline_keyboard":rows}); return
                    if data.startswith("o:gsetlang:"):
                        cid=int(parts[2]); code=parts[3];
                        if code in LANGUAGES: await self.db.set_chat(cid,language=code); await self.db.audit("owner_language",cid,uid,details=f"language={code}")
                        await self._owner_group_settings(callback,cid); return
                except Exception as exc:
                    logging.exception("OWNER_CALLBACK_FAILED data=%s",data)
                    try: await self.api.answer_callback(callback["id"],f"Error: {type(exc).__name__}")
                    except Exception: pass
