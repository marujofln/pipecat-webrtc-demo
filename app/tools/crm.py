import httpx

from app.config import settings
from app.tools.registry import Tool


async def list_available_slots(args: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{settings.crm_base_url}/slots", params={"date": args.get("date", "")})
        r.raise_for_status()
        return r.json()


async def schedule_appointment(args: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            f"{settings.crm_base_url}/appointments",
            json={"patient_name": args["patient_name"], "slot": args["slot"]},
        )
        r.raise_for_status()
        return r.json()


LIST_SLOTS = Tool(
    name="list_available_slots",
    description="Lists available appointment slots, optionally for one date (YYYY-MM-DD).",
    properties={"date": {"type": "string", "description": "Date as YYYY-MM-DD (optional)"}},
    required=[],
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
