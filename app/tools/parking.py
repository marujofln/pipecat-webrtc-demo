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
    description="Abre a cancela do estacionamento para um veículo. Só chame após o usuário confirmar a placa.",
    properties={"plate": {"type": "string", "description": "Placa do veículo, ex: ABC1D23"}},
    required=["plate"],
    handler=open_gate,
)
