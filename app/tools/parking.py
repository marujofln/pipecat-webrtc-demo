import httpx

from app.config import settings
from app.tools.registry import Tool


async def open_gate(args: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{settings.parking_base_url}/gate/open", json={"plate": args["plate"]})
        r.raise_for_status()
        return r.json()


OPEN_GATE = Tool(
    name="open_gate",
    description="Opens the parking gate for a vehicle. Only call after the user confirms the plate.",
    properties={"plate": {"type": "string", "description": "Vehicle plate, e.g. ABC1D23"}},
    required=["plate"],
    handler=open_gate,
)
