import os
from datetime import datetime
import googlemaps
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=API_KEY) if API_KEY else None


def get_transit_route_by_name(
        start_venue: str,
        end_venue: str,
        departure_datetime: datetime
) -> dict:
    """
    Queries Google Directions API using human-readable venue names directly.
    """
    if not gmaps:
        raise ValueError("GOOGLE_MAPS_API_KEY is missing from .env")

    try:
        # Pass strings directly! Append ', Singapore' for strict spatial scoping
        origin_str = f"{start_venue}, Singapore"
        destination_str = f"{end_venue}, Singapore"

        directions = gmaps.directions(
            origin=origin_str,
            destination=destination_str,
            mode="transit",
            departure_time=departure_datetime,
        )

        if not directions:
            return {
                "real_commute_mins": 0,
                "step_by_step": f"No transit route found between {start_venue} and {end_venue}.",
                "start_coords": None,
                "end_coords": None,
            }

        leg = directions[0]["legs"][0]

        # Google returns the exact resolved coordinates for your frontend map pins!
        start_coords = (leg["start_location"]["lat"], leg["start_location"]["lng"])
        end_coords = (leg["end_location"]["lat"], leg["end_location"]["lng"])

        total_duration_mins = round(leg["duration"]["value"] / 60)
        total_distance_m = leg["distance"]["value"]

        legs_summary = []
        for step in leg["steps"]:
            travel_mode = step["travel_mode"]

            if travel_mode == "TRANSIT":
                transit = step["transit_details"]
                line_info = transit["line"]
                vehicle_type = line_info["vehicle"]["type"]  # BUS, SUBWAY, FERRY
                line_name = line_info.get("short_name") or line_info.get("name", "")
                dep_stop = transit["departure_stop"]["name"]
                arr_stop = transit["arrival_stop"]["name"]
                dur_mins = round(step["duration"]["value"] / 60)

                if vehicle_type == "FERRY":
                    legs_summary.append(
                        f"⛵ Take Ferry ({line_name}) from '{dep_stop}' to '{arr_stop}' ({dur_mins} mins)")
                elif vehicle_type == "SUBWAY":
                    legs_summary.append(f"🚇 Take MRT {line_name} from '{dep_stop}' to '{arr_stop}' ({dur_mins} mins)")
                else:
                    legs_summary.append(f"🚌 Take Bus {line_name} from '{dep_stop}' to '{arr_stop}' ({dur_mins} mins)")

            elif travel_mode == "WALKING":
                dist_m = step["distance"]["value"]
                dur_mins = round(step["duration"]["value"] / 60)
                if dist_m > 50:
                    legs_summary.append(f"🚶 Walk {dist_m}m ({dur_mins} mins)")

        return {
            "real_commute_mins": total_duration_mins,
            "walk_distance_m": total_distance_m,
            "step_by_step": " ➔ ".join(legs_summary),
            "start_coords": start_coords,  # Retained for map UI
            "end_coords": end_coords,  # Retained for map UI
        }

    except Exception as e:
        return {
            "real_commute_mins": 0,
            "walk_distance_m": 0,
            "step_by_step": f"Routing error: {e}",
            "start_coords": None,
            "end_coords": None,
        }