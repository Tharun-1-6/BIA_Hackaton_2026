"""Family alerts over Telegram.

A family member joins a specific member by sending /family CODE to the bot. The code comes from the member
(/start or /code in their own chat). Links live in SQLite (pipeline/store.py); alerts only go to the families
linked to that member. There is no preset list: the code is the only way in.
"""
import os
import time

from bia_hackaton_2026.pipeline import store

COOLDOWN_SECONDS = 600                      # no repeat alert of same/lower level for one member within 10 minutes
_LAST_ALERT: dict[str, tuple[int, float]] = {}


async def send_family_alert(bot, elder_chat_id, elder_name: str, alert_text: str, level: int) -> dict:
    """Send the alert to every family chat linked to this member. Returns dict:
    delivered (list of chat ids), failed (chat id -> reason), skipped (reason or ''), registered (int)."""
    out = {"delivered": [], "failed": {}, "skipped": "", "registered": 0}
    # FAMILY_INCLUDE_SELF=1 (demo with one Telegram account): the member's own chat may also receive the alert
    include_self = os.environ.get("FAMILY_INCLUDE_SELF") == "1"
    targets = {c: n for c, n in store.families_of(elder_chat_id).items() if include_self or c != str(elder_chat_id)}
    out["registered"] = len(targets)
    if not targets:
        return out

    last = _LAST_ALERT.get(str(elder_chat_id))
    if last and level <= last[0] and time.time() - last[1] < COOLDOWN_SECONDS:
        out["skipped"] = "same or higher level alert already sent in the last 10 minutes"
        out["delivered"] = ["(earlier alert)"]
        return out

    icon = {3: "🚨 EMERGENCY", 2: "⚠️ CHECK IN"}.get(level, "ℹ️ UPDATE")
    text = (f"{icon} - SAHAYI\n\nMember: {elder_name}\n\n{alert_text.replace('*', '')}\n\n"
            "Please check on them now. If it is an emergency, call 112 yourself.")
    for cid in targets:
        try:
            await bot.send_message(int(cid), text)
            out["delivered"].append(cid)
        except Exception as e:  # e.g. the family member blocked the bot
            out["failed"][cid] = str(e)[:150]
    if out["delivered"]:
        _LAST_ALERT[str(elder_chat_id)] = (level, time.time())
    return out
