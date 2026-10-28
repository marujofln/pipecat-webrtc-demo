import re

import httpx

from app.config import settings
from app.tools.registry import Tool

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SLOT_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")


async def list_available_slots(args: dict) -> dict:
    date = args.get("date") or ""
    if date and not DATE_RE.fullmatch(date):
        raise ValueError("date must be YYYY-MM-DD")
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{settings.crm_base_url}/slots", params={"date": date})
        r.raise_for_status()
        return r.json()


async def schedule_appointment(args: dict) -> dict:
    name, slot = str(args["patient_name"]).strip(), str(args["slot"])
    if not 1 <= len(name) <= 100 or not name.isprintable():
        raise ValueError("patient_name must be 1-100 printable characters")
    if not SLOT_RE.fullmatch(slot):
        raise ValueError("slot must be exactly as returned by list_available_slots")
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"{settings.crm_base_url}/appointments",
            json={"patient_name": name, "slot": slot},
        )
        r.raise_for_status()
        return r.json()


LIST_SLOTS = Tool(
    name="list_available_slots",
    description="Lists available appointment slots, optionally for one date (YYYY-MM-DD).",
    # Required and never null: Groq rejects a null for a string field, so "" means any date.
    properties={"date": {"type": "string", "description": "Date as YYYY-MM-DD, or an empty string for any date"}},
    required=["date"],
    handler=list_available_slots,
)

SCHEDULE = Tool(
    name="schedule_appointment",
    description="Books an appointment in the CRM. Only call after the user confirms name and slot.",
    properties={
        "patient_name": {"type": "string", "description": "Patient name"},
        "slot": {"type": "string", "description": "Chosen slot, exactly as returned by list_available_slots"},
    },
    required=["patient_name", "slot"],
    handler=schedule_appointment,
)
