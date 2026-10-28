"""WhatsApp Business Calling API: `calls` webhook parsing and call actions via the Graph API.

Inbound (user-initiated) call flow:
  webhook event=connect (SDP offer) → pre_accept(answer) → accept(answer) → WebRTC media
  webhook event=terminate → ends the local session
"""

import hashlib
import hmac
from dataclasses import dataclass

import httpx
from loguru import logger

from app.config import settings

GRAPH_URL = "https://graph.facebook.com/v23.0"


@dataclass
class CallEvent:
    call_id: str
    event: str  # "connect" | "terminate" | ...
    caller: str
    sdp: str | None = None
    sdp_type: str | None = None


def verify_signature(body: bytes, header: str | None, app_secret: str) -> bool:
    if not app_secret:
        logger.error("WHATSAPP_APP_SECRET is empty: rejecting webhook (signature cannot be verified)")
        return False
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def parse_call_events(payload: dict) -> list[CallEvent]:
    events = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "calls":
                continue
            for call in change.get("value", {}).get("calls", []):
                if not isinstance(call, dict) or not call.get("id"):
                    continue
                session = call.get("session") or {}
                events.append(
                    CallEvent(
                        call_id=call["id"],
                        event=call.get("event", ""),
                        caller=call.get("from", ""),
                        sdp=session.get("sdp"),
                        sdp_type=session.get("sdp_type"),
                    )
                )
    return events


async def call_action(call_id: str, action: str, sdp: str | None = None) -> dict:
    if not (settings.whatsapp_access_token and settings.whatsapp_phone_number_id):
        raise RuntimeError("Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env")
    body = {"messaging_product": "whatsapp", "call_id": call_id, "action": action}
    if sdp:
        body["session"] = {"sdp_type": "answer", "sdp": sdp}
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"{GRAPH_URL}/{settings.whatsapp_phone_number_id}/calls",
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            json=body,
        )
    if r.is_error:
        logger.error(f"WhatsApp {action} failed ({r.status_code}): {r.text}")
    r.raise_for_status()
    return r.json()
