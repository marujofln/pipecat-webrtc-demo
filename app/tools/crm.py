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
    description="Lista horários de consulta disponíveis, opcionalmente para uma data (AAAA-MM-DD).",
    properties={"date": {"type": "string", "description": "Data no formato AAAA-MM-DD (opcional)"}},
    required=[],
    handler=list_available_slots,
)

SCHEDULE = Tool(
    name="schedule_appointment",
    description="Marca uma consulta no CRM. Só chame após o usuário confirmar nome e horário.",
    properties={
        "patient_name": {"type": "string", "description": "Nome do paciente"},
        "slot": {"type": "string", "description": "Horário escolhido, exatamente como retornado por list_available_slots"},
    },
    required=["patient_name", "slot"],
    handler=schedule_appointment,
)
