"""Mock CRM API. Run: uvicorn mock_apis.server:app --port 8002"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Mock CRM", docs_url=None, redoc_url=None, openapi_url=None)
SLOTS = ["2026-11-03 09:00", "2026-11-03 14:30", "2026-11-04 10:00"]
APPOINTMENTS: list[dict] = []


class Appointment(BaseModel):
    patient_name: str = Field(min_length=1, max_length=100)
    slot: str = Field(max_length=32)


@app.get("/crm/slots")
def slots(date: str = ""):
    taken = {a["slot"] for a in APPOINTMENTS}
    return {"slots": [s for s in SLOTS if s not in taken and s.startswith(date)]}


@app.post("/crm/appointments")
def create_appointment(body: Appointment):
    if body.slot not in SLOTS:
        raise HTTPException(422, "unknown slot")
    if any(a["slot"] == body.slot for a in APPOINTMENTS):
        raise HTTPException(409, "slot already taken")
    appt = {"id": len(APPOINTMENTS) + 1, **body.model_dump()}
    APPOINTMENTS.append(appt)
    return {"status": "confirmed", **appt}
