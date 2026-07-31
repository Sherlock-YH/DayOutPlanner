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
class ItineraryStop(BaseModel):
    venue_name: str = Field(
        description="Exact well-known name of the venue in Singapore (e.g., 'National Gallery Singapore', 'Maxwell Food Centre')."
    )
    category: str = Field(description="Category e.g., 'Sightseeing', 'Food', 'Nature'")
    stay_duration_minutes: int = Field(description="Recommended stay duration in minutes.")
    why_go: str = Field(description="Short 1-sentence reason to visit.")


class ItineraryResponse(BaseModel):
    title: str
    summary: str
    stops: list[ItineraryStop]


# ==========================================
# 2. LLM Planner Generator
# ==========================================
def generate_itinerary_plan(user_prompt: str) -> ItineraryResponse:
    """Uses GPT-4o-mini to generate structured venue stops based on user preferences."""
    system_prompt = (
        "You are an expert Singapore travel planner and spatial logistics coordinator.\n\n"
        "RULES FOR ITINERARY STOPS:\n"
        "1. DESTINATIONS ONLY: Every stop MUST be a genuine point of interest. NEVER include transit stations or MRT stops as itinerary stops.\n"
        "2. REAL & OPERATIONAL VENUES ONLY: Use active, currently operating venue names in Singapore (e.g., use 'Bee's Knees at Garage' or 'The Halia' instead of closed venues like 'Food for Thought'). For local food, name the Hawker Centre or Food Complex (e.g., 'Maxwell Food Centre', 'Chinatown Complex') rather than individual stall names.\n"
        "3. IMMEDIATE PAIRING: When pairing an outdoor attraction with a meal stop, select a dining option located directly inside or within a 5-minute walk of that attraction before moving to another district.\n"
        "4. GEOGRAPHIC EFFICIENCY: Order stops logically across Singapore to minimize transit time.\n"
        "5. SPECIFIC PARK ENTRANCES: For sprawling nature reserves, specify a known entrance (e.g., 'MacRitchie Reservoir Mushroom Cafe Entrance', 'East Coast Park Parkland Green').\n"
        "6. NO DISTANCE CLAIMS IN RATIONALE: Do not make proximity or distance claims in 'why_go'. Leave all distance and travel calculations entirely to the routing engine."
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=ItineraryResponse,
    )

    return completion.choices[0].message.parsed


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