# app.py
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from main import generate_itinerary_plan

app = FastAPI(title="DayOutPlanner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlanRequest(BaseModel):
    prompt: str
    start_location: str = "Marina Bay Sands, Singapore"  # Default fallback
    start_time: str = "09:00 AM"                        # Default fallback


@app.post("/api/plan")
def create_itinerary(req: PlanRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    try:
        return generate_itinerary_plan(
            prompt=req.prompt,
            start_location=req.start_location,
            start_time_str=req.start_time
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))