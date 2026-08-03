import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

# Import Google Maps transit service
from gmaps_service import get_transit_route_by_name

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ==========================================
# 1. Pydantic Schema
# ==========================================
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
# 2. LLM Planner Generator
# ==========================================
def generate_itinerary_plan(
    prompt: str,
    start_location: str = "Marina Bay Sands, Singapore",
    start_time_str: str = "09:00 AM",
):
    """
    1. Calls OpenAI GPT-4o with structured outputs using start_location & start_time.
    2. Calculates initial commute from start_location to Stop #1.
    3. Runs Google Maps Transit router between sequential stops.
    4. Calculates real arrival/departure clock times.
    5. Attaches 'initial_transit', 'transit_to_next', and coordinates to the output.
    6. Returns a rich dictionary for the FastAPI/Next.js frontend.
    """
    # 1. Parse user's start time (Supports "09:00 AM", "9:00 AM", or "09:00")
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

    # If the requested start time has already passed today, roll over to tomorrow!
    if current_time < now:
        current_time += timedelta(days=1)

    # 2. System prompt with explicit starting location & time guidelines
    system_prompt = (
        "You are an expert Singapore travel planner and spatial logistics coordinator.\n\n"
        f"USER STARTING POINT: '{start_location}' at {start_time_str}.\n"
        "Plan a realistic itinerary where Stop #1 is logically reached from the starting point.\n\n"
        "RULES FOR ITINERARY STOPS:\n"
        "1. DESTINATIONS ONLY: Every stop MUST be a genuine point of interest. NEVER include transit stations or MRT stops.\n"
        "2. OPERATIONAL & CURRENT VENUES ONLY: Use active, currently operating venues in Singapore.\n"
        "3. STRICT THEME ADHERENCE: Strictly match the user's prompt (e.g., if 'INDOOR' is requested, choose air-conditioned museums, glass domes, malls, covered hawker complexes).\n"
        "4. NO GEOGRAPHIC BACKTRACKING: Fully explore a single neighborhood/district before moving to the next. NEVER route the user back to a previously visited neighborhood later in the day.\n"
        "5. SAME-BUILDING PAIRING: When pairing an attraction with dining in the same building, explicitly state the building in both stop names so the routing engine recognizes proximity.\n"
        "6. SPECIFIC PARK ENTRANCES: Specify known entrances (e.g., 'MacRitchie Reservoir Mushroom Cafe Entrance').\n"
        "7. NO DISTANCE CLAIMS IN RATIONALE: Leave all transit calculations entirely to the routing engine.\n"
        "8. DISTANCE BETWEEN EACH STOP NEEDS TO BE REASONABLE: To mitigate the travelling time for users."
    )

    # 3. Query OpenAI for structured itinerary
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

    # 4. Calculate commute from Start Location -> Stop #1
    initial_transit_info = None
    if num_stops > 0:
        first_stop = parsed_plan.stops[0]
        initial_transit = get_transit_route_by_name(
            start_venue=start_location,
            end_venue=first_stop.venue_name,
            departure_datetime=current_time,
        )

        # Prioritize drive_mins over real_commute_mins
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

        # Advance current time by initial commute duration
        current_time += timedelta(minutes=initial_commute_mins)

    formatted_stops = []
    last_end_coords = None

    # 5. Process each stop and compute transit to next
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

        # Safe coordinate & transit assignment to next stop
        if i < num_stops - 1:
            next_venue = parsed_plan.stops[i + 1].venue_name
            transit_info = get_transit_route_by_name(
                start_venue=stop.venue_name,
                end_venue=next_venue,
                departure_datetime=departure_time,
            )

            # Safely extract start coordinates for current stop
            start_coords = (
                transit_info.get("start_coords") if isinstance(transit_info, dict) else None
            )
            if isinstance(start_coords, dict):
                stop_dict["lat"] = start_coords.get("lat")
                stop_dict["lng"] = start_coords.get("lng")

            # Store end coordinates to use for the final stop
            end_coords = (
                transit_info.get("end_coords") if isinstance(transit_info, dict) else None
            )
            if isinstance(end_coords, dict):
                last_end_coords = end_coords

            # Correct key fallback matching gmaps_service.py
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
            # Final stop gets coordinates from previous transit end location
            if isinstance(last_end_coords, dict):
                stop_dict["lat"] = last_end_coords.get("lat")
                stop_dict["lng"] = last_end_coords.get("lng")
            current_time = departure_time

        formatted_stops.append(stop_dict)

    # 6. Return structured dictionary
    return {
        "title": parsed_plan.title,
        "summary": parsed_plan.summary,
        "start_location": start_location,
        "start_time": start_time_str,
        "initial_transit": initial_transit_info,
        "stops": formatted_stops,
    }


# ==========================================
# 3. Main Route Execution Engine (CLI Test)
# ==========================================
def run_itinerary(
    user_prompt: str,
    start_location: str = "Marina Bay Sands, Singapore",
    start_time_str: str = "09:00 AM",
):
    print(f"🤖 Generating AI itinerary plan for: '{user_prompt}'...")
    print(f"📍 Starting Point: {start_location} at {start_time_str}\n")

    plan = generate_itinerary_plan(
        prompt=user_prompt,
        start_location=start_location,
        start_time_str=start_time_str,
    )

    print(f"📌 {plan['title']}")
    print(f"📝 {plan['summary']}\n")
    print("=" * 60)

    if plan.get("initial_transit"):
        init_t = plan["initial_transit"]
        print(f"🚩 START: {init_t['start_location']}")
        print(f"   🚍 COMMUTE TO STOP #1 ({init_t['commute_mins']} mins):")
        print(f"      {init_t['step_by_step']}\n")
        print("-" * 60)

    for stop in plan["stops"]:
        stop_num = stop["stop_number"]
        print(f"📍 Stop #{stop_num}: {stop['venue_name']}")
        print(f"   ⏰ Time: {stop['start_time']} – {stop['end_time']} ({stop['duration_mins']} mins)")
        print(f"   💡 {stop['why_go']}")

        transit = stop.get("transit_to_next")
        if transit:
            print(f"\n   🚍 TRANSIT TO NEXT ({transit['commute_mins']} mins):")
            print(f"      {transit['step_by_step']}\n")
        print("-" * 60)

    return plan


# ==========================================
# 4. Entrypoint Test
# ==========================================
if __name__ == "__main__":
    test_prompt = "A 1-day outdoor nature and local food tour in Singapore"
    run_itinerary(
        user_prompt=test_prompt,
        start_location="Changi Airport Terminal 3",
        start_time_str="08:30 AM",
    )