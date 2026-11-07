"""Family alerts over Telegram.

Family members register by sending /family to the Sahayi bot. Their chat IDs are kept in
family_chats.json (next to this file, git-ignored) and can also be preset in .env:
  FAMILY_TELEGRAM_CHAT_IDS=123456789,987654321
"""
import json
import os
import time
from pathlib import Path

REGISTRY = Path(__file__).parent / "family_chats.json"
COOLDOWN_SECONDS = 600                      # no repeat alert of same/lower level for one elder within 10 minutes
_LAST_ALERT: dict[str, tuple[int, float]] = {}


def _load() -> dict[str, str]:
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def family_chat_ids() -> dict[str, str]:
    """chat_id -> display name, from the registry plus FAMILY_TELEGRAM_CHAT_IDS."""
    ids = _load()
    for raw in os.environ.get("FAMILY_TELEGRAM_CHAT_IDS", "").split(","):
        raw = raw.strip()
        if raw.lstrip("-").isdigit():
            ids.setdefault(raw, "family")
    return ids


def add_family(chat_id, name: str) -> None:
    ids = _load()
    ids[str(chat_id)] = name
    REGISTRY.write_text(json.dumps(ids, ensure_ascii=False, indent=1), encoding="utf-8")


def remove_family(chat_id) -> bool:
    ids = _load()
    existed = ids.pop(str(chat_id), None) is not None
    REGISTRY.write_text(json.dumps(ids, ensure_ascii=False, indent=1), encoding="utf-8")
    return existed


def is_family(chat_id) -> bool:
    return str(chat_id) in family_chat_ids()


async def send_family_alert(bot, elder_chat_id, elder_name: str, alert_text: str, level: int) -> dict:
    """Send the alert to every registered family chat. Returns dict:
    delivered (list of chat ids), failed (chat id -> reason), skipped (reason or ''), registered (int)."""
    out = {"delivered": [], "failed": {}, "skipped": "", "registered": 0}
    # FAMILY_INCLUDE_SELF=1 (demo with one Telegram account): the elder's own chat may also receive the alert
    include_self = os.environ.get("FAMILY_INCLUDE_SELF") == "1"
    targets = {c: n for c, n in family_chat_ids().items() if include_self or c != str(elder_chat_id)}
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
        except Exception as e:  # e.g. the family member has not started the bot, or blocked it
            out["failed"][cid] = str(e)[:150]
    if out["delivered"]:
        _LAST_ALERT[str(elder_chat_id)] = (level, time.time())
    return out
