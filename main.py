from datetime import datetime, timedelta
from dotenv import load_dotenv

from poc import generate_singapore_itinerary
from onemap_route import get_onemap_token, get_public_transit_route, parse_route_summary

load_dotenv()


def build_verified_itinerary_pipeline(prompt: str, start_datetime: datetime):
    """
    Complete Pipeline:
    1. Calls OpenAI LLM to get structured itinerary stops.
    2. Obtains SLA OneMap token.
    3. Chronologically calculates real transit times using OneMap API.
    4. Overrides LLM commute claims with verified transit data.
    """
    print(f"🤖 Step 1: Generating LLM Itinerary for: '{prompt}'...")
    itinerary = generate_singapore_itinerary(prompt)

    print("🔑 Step 2: Authenticating with SLA OneMap API...")
    token = get_onemap_token()

    print("🚇 Step 3: Verifying travel times & building chronological timeline...\n")

    current_time = start_datetime

    print("=" * 65)
    print(f"📌 {itinerary.title}")
    print(f"👥 Target: {itinerary.target_audience} | 📅 Day Type: {itinerary.day_type}")
    print(f"🗓️ Start Date & Time: {start_datetime.strftime('%A, %b %d, %Y @ %I:%M %p')}")
    print("=" * 65 + "\n")

    for i in range(len(itinerary.stops)):
        stop = itinerary.stops[i]

        # 1. Calculate venue visit window
        arrival_time_str = current_time.strftime("%I:%M %p")
        current_time += timedelta(minutes=stop.estimated_duration_mins)
        departure_time_str = current_time.strftime("%I:%M %p")

        print(f"Stop {stop.stop_number}: {stop.venue_name} [{stop.category}]")
        print(f"  🕒 Time at Venue: {arrival_time_str} - {departure_time_str} ({stop.estimated_duration_mins} mins)")
        print(f"  💡 Why Go: {stop.reason}")
        print(f"  📍 Coords: ({stop.lat}, {stop.lng})")

        # 2. If there is a next stop, calculate transit starting at departure_time_str
        if i < len(itinerary.stops) - 1:
            next_stop = itinerary.stops[i + 1]

            try:
                raw_route = get_public_transit_route(
                    start_lat=stop.lat,
                    start_lng=stop.lng,
                    end_lat=next_stop.lat,
                    end_lng=next_stop.lng,
                    token=token,
                    departure_datetime=current_time  # Pass planned departure time!
                )
                summary = parse_route_summary(raw_route)

                # Overwrite LLM's commute tips with verified OneMap data
                next_stop.commute_tips_from_previous = (
                    f"Verified Commute ({summary['real_commute_mins']} mins): {summary['step_by_step']}"
                )

                print(f"\n  🚇 Transit to {next_stop.venue_name}:")
                print(f"     Departing at: {departure_time_str}")
                print(f"     Route: {summary['step_by_step']}")
                print(f"     Real Travel Duration: {summary['real_commute_mins']} mins")

                # Advance clock by actual commute duration before the next stop
                current_time += timedelta(minutes=summary["real_commute_mins"])

            except Exception as e:
                print(f"  ⚠️ Could not fetch OneMap route: {e}")

        print("\n" + "-" * 65 + "\n")

    return itinerary


if __name__ == "__main__":
    user_prompt = "Generate a relaxed Saturday itinerary in Singapore focusing on nature and local hawker food."

    # Departure Date: Next Saturday at 9:00 AM
    planned_start_time = datetime(2026, 8, 1, 9, 0, 0)

    verified_itinerary = build_verified_itinerary_pipeline(user_prompt, planned_start_time)