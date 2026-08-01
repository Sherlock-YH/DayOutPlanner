import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# Import our new Google Maps transit service
from gmaps_service import get_transit_route_by_name

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ==========================================
# 1. Pydantic Schema (No Lat/Lng Needed!)
# ==========================================
# Define Pydantic schema for structured output
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
def generate_itinerary_plan(user_prompt: str) -> dict:
    """
    1. Calls OpenAI GPT-4o with structured outputs to get stops.
    2. Runs Google Maps Transit router between sequential stops.
    3. Calculates real arrival/departure clock times.
    4. Attaches 'transit_to_next' to each stop object.
    5. Returns a rich, clean dictionary for the FastAPI/Next.js frontend.
    """
    system_prompt = (
        "You are an expert Singapore travel planner and spatial logistics coordinator.\n\n"
        "RULES FOR ITINERARY STOPS:\n"
        "1. DESTINATIONS ONLY: Every stop MUST be a genuine point of interest. NEVER include transit stations or MRT stops.\n"
        "2. OPERATIONAL & CURRENT VENUES ONLY: Use active, currently operating venues in Singapore. (DO NOT use closed venues like Chinatown Heritage Centre or Food for Thought).\n"
        "3. STRICT THEME ADHERENCE: Strictly match the user's prompt (e.g., if 'INDOOR' is requested, choose air-conditioned museums, glass domes, malls, and covered hawker complexes like Lau Pa Sat—DO NOT include outdoor walking streets like Haji Lane or East Coast Park).\n"
        "4. NO GEOGRAPHIC BACKTRACKING: Fully explore a single neighborhood/district (e.g., Marina Bay, Bugis, Chinatown) before moving to the next. NEVER route the user back to a previously visited neighborhood later in the day.\n"
        "5. SAME-BUILDING PAIRING: When pairing an attraction with dining in the same building (e.g., museum cafe), explicitly state the building in both stop names so the routing engine recognizes proximity.\n"
        "6. SPECIFIC PARK ENTRANCES: Specify known entrances (e.g., 'MacRitchie Reservoir Mushroom Cafe Entrance').\n"
        "7. NO DISTANCE CLAIMS IN RATIONALE: Leave all transit calculations entirely to the routing engine."
    )

    # 1. Query OpenAI for structured itinerary
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a realistic Singapore itinerary for: '{user_prompt}'"},
        ],
        response_format=ItineraryPlan,
    )

    parsed_plan = completion.choices[0].message.parsed

    # 2. Start clock at 09:00 AM today
    current_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    formatted_stops = []
    num_stops = len(parsed_plan.stops)
    last_end_coords = None  # Prevents UnboundLocalError

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

        # Safe coordinate assignment
        if i < num_stops - 1:
            next_venue = parsed_plan.stops[i + 1].venue_name
            transit_info = get_transit_route_by_name(
                start_venue=stop.venue_name,
                end_venue=next_venue,
                departure_datetime=departure_time,
            )

            # Safely extract start coordinates for current stop
            start_coords = transit_info.get("start_coords") if isinstance(transit_info, dict) else None
            if isinstance(start_coords, dict):
                stop_dict["lat"] = start_coords.get("lat")
                stop_dict["lng"] = start_coords.get("lng")

            # Store end coordinates to use for the final stop
            end_coords = transit_info.get("end_coords") if isinstance(transit_info, dict) else None
            if isinstance(end_coords, dict):
                last_end_coords = end_coords

            commute_mins = transit_info.get("real_commute_mins", 0) if isinstance(transit_info, dict) else 0
            step_text = transit_info.get("step_by_step", "Direct route") if isinstance(transit_info,
                                                                                       dict) else "Direct route"

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

    # 4. Return final dictionary
    return {
        "title": parsed_plan.title,
        "summary": parsed_plan.summary,
        "stops": formatted_stops,
    }


# ==========================================
# 3. Main Route Execution Engine
# ==========================================
def run_itinerary(user_prompt: str, start_time: datetime = None):
    # Default start time: Today at 9:00 AM
    if not start_time:
        start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    print(f"🤖 Generating AI itinerary plan for: '{user_prompt}'...\n")
    plan = generate_itinerary_plan(user_prompt)

    print(f"📌 {plan.title}")
    print(f"📝 {plan.summary}\n")
    print("=" * 60)

    current_time = start_time
    final_itinerary = []

    for i, stop in enumerate(plan.stops):
        stop_number = i + 1

        # If this is NOT the first stop, calculate transit from the previous venue
        transit_info = None
        if i > 0:
            prev_venue = plan.stops[i - 1].venue_name
            curr_venue = stop.venue_name

            # Query Google Maps API with place names directly!
            transit_info = get_transit_route_by_name(
                start_venue=prev_venue,
                end_venue=curr_venue,
                departure_datetime=current_time,
            )

            # Advance clock by transit time
            commute_mins = transit_info["real_commute_mins"]
            current_time += timedelta(minutes=commute_mins)

        arrival_time_str = current_time.strftime("%I:%M %p")

        # Calculate departure time after stay duration
        current_time += timedelta(minutes=stop.stay_duration_minutes)
        departure_time_str = current_time.strftime("%I:%M %p")

        stop_detail = {
            "step": stop_number,
            "venue": stop.venue_name,
            "category": stop.category,
            "arrival_time": arrival_time_str,
            "departure_time": departure_time_str,
            "stay_duration_mins": stop.stay_duration_minutes,
            "why_go": stop.why_go,
            "transit_from_previous": transit_info["step_by_step"] if transit_info else None,
        }
        final_itinerary.append(stop_detail)

        # Print formatted readable console logs
        if transit_info:
            print(f"\n   🚍 TRANSIT ({transit_info['real_commute_mins']} mins):")
            print(f"      {transit_info['step_by_step']}\n")

        print(f"📍 Stop #{stop_number}: {stop.venue_name}")
        print(f"   ⏰ Time: {arrival_time_str} – {departure_time_str} ({stop.stay_duration_minutes} mins)")
        print(f"   💡 {stop.why_go}")
        print("-" * 60)

    return final_itinerary


# ==========================================
# 4. Entrypoint Test
# ==========================================
if __name__ == "__main__":
    test_prompt = "A 1-day outdoor nature and local food tour in Singapore"
    run_itinerary(test_prompt)