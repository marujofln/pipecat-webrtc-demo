"""Mock CRM API. Run: uvicorn mock_apis.server:app --port 8002"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock CRM")
SLOTS = ["2026-11-03 09:00", "2026-11-03 14:30", "2026-11-04 10:00"]
APPOINTMENTS: list[dict] = []


class Appointment(BaseModel):
    patient_name: str
    slot: str


@app.get("/crm/slots")
def slots(date: str = ""):
    taken = {a["slot"] for a in APPOINTMENTS}
    return {"slots": [s for s in SLOTS if s not in taken and s.startswith(date)]}


@app.post("/crm/appointments")
def create_appointment(body: Appointment):
    appt = {"id": len(APPOINTMENTS) + 1, **body.model_dump()}
    APPOINTMENTS.append(appt)
    return {"status": "confirmed", **appt}

