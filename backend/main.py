import json
import os
import sys
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel

# Import Google Maps transit service
from gmaps_service import get_transit_route_by_name

# Ensure Python defaults standard I/O to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()
client = OpenAI()


# ==========================================
# 0. Unicode-safe JSON Response
# ==========================================
# FastAPI's default JSONResponse uses `ensure_ascii=True`, which raises a
# UnicodeEncodeError when the payload contains non-ASCII characters (e.g.
# the \u2028 line separator that OpenAI sometimes returns). Using
# `ensure_ascii=False` lets the response body be encoded as UTF-8 instead.
class UnicodeJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


app = FastAPI(title="DayOutPlanner API", default_response_class=UnicodeJSONResponse)

# ==========================================
# 1. CORS Configuration
# ==========================================
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://dayout-planner.vercel.app",
    "https://dayout.sherlock-yh.top",
]

frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 2. Pydantic Schemas
# ==========================================
class PlanRequest(BaseModel):
    prompt: str
    start_location: str = "Marina Bay Sands, Singapore"
    start_time: str = "09:00 AM"


class ItineraryStop(BaseModel):
    stop_number: int
    venue_name: str
    stay_duration_mins: int
    why_go: str


class ItineraryPlan(BaseModel):
    title: str
    summary: str
    stops: list[ItineraryStop]


# ==========================================
# 3. API Endpoints
# ==========================================
@app.post("/api/plan")
@app.post("/plan")
def create_itinerary(req: PlanRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    try:
        return generate_itinerary_plan(
            prompt=req.prompt.replace("\u2028", " "),
            start_location=req.start_location.replace("\u2028", " "),
            start_time_str=req.start_time.replace("\u2028", " ")
        )
    except Exception as e:
        traceback.print_exc()
        # Clean exception message to prevent ASCII encoding crashes
        error_msg = str(e).encode("utf-8", "ignore").decode("utf-8").replace("\u2028", " ")
        raise HTTPException(status_code=500, detail=error_msg)


# ==========================================
# 4. LLM Planner Generator
# ==========================================
def generate_itinerary_plan(
    prompt: str,
    start_location: str = "Marina Bay Sands, Singapore",
    start_time_str: str = "09:00 AM",
):
    # Sanitize inputs to strip invisible Unicode line separators
    prompt = prompt.replace("\u2028", "\n").replace("\u2029", "\n").strip()
    start_location = start_location.replace("\u2028", " ").replace("\u2029", " ").strip()
    start_time_str = start_time_str.replace("\u2028", " ").replace("\u2029", " ").strip()

    now = datetime.now()
    try:
        clean_time_str = start_time_str.strip()
        if "AM" in clean_time_str.upper() or "PM" in clean_time_str.upper():
            base_time = datetime.strptime(clean_time_str, "%I:%M %p")
        else:
            base_time = datetime.strptime(clean_time_str, "%H:%M")

        current_time = datetime.now().replace(
            hour=base_time.hour, minute=base_time.minute, second=0, microsecond=0
        )
    except ValueError:
        current_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    if current_time < now:
        current_time += timedelta(days=1)

    # Clean multi-line system prompt without hidden unicode characters
    system_prompt = (
        "You are an expert Singapore travel planner and spatial logistics coordinator.\n\n"
        f"USER STARTING POINT: {start_location} at {start_time_str}.\n"
        "Plan a realistic itinerary where Stop 1 is logically reached from the starting point.\n\n"
        "RULES FOR ITINERARY STOPS:\n"
        "1. DESTINATIONS ONLY: Every stop MUST be a genuine point of interest. NEVER include transit stations or MRT stops.\n"
        "2. OPERATIONAL & CURRENT VENUES ONLY: Use active, currently operating venues in Singapore.\n"
        "3. STRICT THEME ADHERENCE: Strictly match the user prompt (e.g. if INDOOR is requested, choose air-conditioned museums, glass domes, malls, covered hawker complexes).\n"
        "4. NO GEOGRAPHIC BACKTRACKING: Fully explore a single neighborhood/district before moving to the next. NEVER route the user back to a previously visited neighborhood later in the day.\n"
        "5. SAME-BUILDING PAIRING: When pairing an attraction with dining in the same building, explicitly state the building in both stop names so the routing engine recognizes proximity.\n"
        "6. SPECIFIC PARK ENTRANCES: Specify known entrances.\n"
        "7. NO DISTANCE CLAIMS IN RATIONALE: Leave all transit calculations entirely to the routing engine.\n"
        "8. REASONABLE DISTANCES: Keep travel distances between stops manageable."
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a realistic Singapore itinerary for: '{prompt}'"},
        ],
        response_format=ItineraryPlan,
    )

    parsed_plan = completion.choices[0].message.parsed
    num_stops = len(parsed_plan.stops)

    initial_transit_info = None
    if num_stops > 0:
        first_stop = parsed_plan.stops[0]
        initial_transit = get_transit_route_by_name(
            start_venue=start_location,
            end_venue=first_stop.venue_name,
            departure_datetime=current_time,
        )

        if isinstance(initial_transit, dict):
            initial_commute_mins = (
                initial_transit.get("drive_mins")
                or initial_transit.get("real_commute_mins")
                or 0
            )
        else:
            initial_commute_mins = 0

        step_text = (
            initial_transit.get("step_by_step", "Direct route")
            if isinstance(initial_transit, dict)
            else "Direct route"
        )

        initial_transit_info = {
            "start_location": start_location,
            "to_venue": first_stop.venue_name,
            "commute_mins": initial_commute_mins,
            "step_by_step": step_text,
            "start_coords": initial_transit.get("start_coords") if isinstance(initial_transit, dict) else None,
        }

        current_time += timedelta(minutes=initial_commute_mins)

    formatted_stops = []
    last_end_coords = None

    for i, stop in enumerate(parsed_plan.stops):
        arrival_str = current_time.strftime("%I:%M %p")
        departure_time = current_time + timedelta(minutes=stop.stay_duration_mins)
        departure_str = departure_time.strftime("%I:%M %p")

        stop_dict = {
            "stop_number": i + 1,
            "venue_name": stop.venue_name,
            "start_time": arrival_str,
            "end_time": departure_str,
            "duration_mins": stop.stay_duration_mins,
            "why_go": stop.why_go,
            "lat": None,
            "lng": None,
            "transit_to_next": None,
        }

        if i < num_stops - 1:
            next_venue = parsed_plan.stops[i + 1].venue_name
            transit_info = get_transit_route_by_name(
                start_venue=stop.venue_name,
                end_venue=next_venue,
                departure_datetime=departure_time,
            )

            start_coords = (
                transit_info.get("start_coords") if isinstance(transit_info, dict) else None
            )
            if isinstance(start_coords, dict):
                stop_dict["lat"] = start_coords.get("lat")
                stop_dict["lng"] = start_coords.get("lng")

            end_coords = (
                transit_info.get("end_coords") if isinstance(transit_info, dict) else None
            )
            if isinstance(end_coords, dict):
                last_end_coords = end_coords

            if isinstance(transit_info, dict):
                commute_mins = (
                    transit_info.get("drive_mins")
                    or transit_info.get("real_commute_mins")
                    or 0
                )
            else:
                commute_mins = 0

            step_text = (
                transit_info.get("step_by_step", "Direct route")
                if isinstance(transit_info, dict)
                else "Direct route"
            )

            stop_dict["transit_to_next"] = {
                "commute_mins": commute_mins,
                "step_by_step": step_text,
            }
            current_time = departure_time + timedelta(minutes=commute_mins)
        else:
            if isinstance(last_end_coords, dict):
                stop_dict["lat"] = last_end_coords.get("lat")
                stop_dict["lng"] = last_end_coords.get("lng")
            current_time = departure_time

        formatted_stops.append(stop_dict)

    return {
        "title": parsed_plan.title,
        "summary": parsed_plan.summary,
        "start_location": start_location,
        "start_time": start_time_str,
        "initial_transit": initial_transit_info,
        "stops": formatted_stops,
    }

@app.get("/")
def health_check():
    return {"status": "online", "message": "DayOutPlanner API is running!"}

# ==========================================
# 5. CLI Test Runner
# ==========================================
if __name__ == "__main__":
    test_prompt = "A 1-day outdoor nature and local food tour in Singapore"
    generate_itinerary_plan(
        prompt=test_prompt,
        start_location="Changi Airport Terminal 3",
        start_time_str="08:30 AM",
    )