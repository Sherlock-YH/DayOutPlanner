import os
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

ONEMAP_EMAIL = os.getenv("ONEMAP_EMAIL")
ONEMAP_PASSWORD = os.getenv("ONEMAP_PASSWORD")


def get_onemap_token(email: str = None, password: str = None) -> str:
    """Authenticates with SLA OneMap API and returns an access token."""
    email = email or ONEMAP_EMAIL
    password = password or ONEMAP_PASSWORD

    if not email or not password:
        raise ValueError("ONEMAP_EMAIL and ONEMAP_PASSWORD must be set in your .env file.")

    url = "https://www.onemap.gov.sg/api/auth/post/getToken"
    payload = {"email": email, "password": password}

    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["access_token"]


def get_public_transit_route(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    token: str,
    departure_datetime: datetime
) -> dict:
    """Queries SLA OneMap Routing API using the exact planned departure timestamp."""
    url = "https://www.onemap.gov.sg/api/public/routingsvc/route"

    # OneMap API required formatting
    date_str = departure_datetime.strftime("%m-%d-%Y")  # MM-DD-YYYY
    time_str = departure_datetime.strftime("%H:%M:%S")  # HH:MM:SS (24-hour)

    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "start": f"{start_lat},{start_lng}",
        "end": f"{end_lat},{end_lng}",
        "routeType": "pt",        # Public Transport
        "mode": "TRANSIT",        # Combines MRT + Bus + Walk
        "date": date_str,
        "time": time_str,
        "maxWalkDistance": "1000",
        "numItineraries": "1",
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def parse_route_summary(route_data: dict) -> dict:
    """Parses raw OneMap transit JSON into a clean summary dict."""
    plan = route_data.get("plan", {})
    itineraries = plan.get("itineraries", [])

    if not itineraries:
        return {
            "real_commute_mins": 0,
            "walk_distance_m": 0,
            "step_by_step": "No direct public transit route found.",
        }

    best_route = itineraries[0]
    total_mins = round(best_route.get("duration", 0) / 60)
    walk_dist = round(best_route.get("walkDistance", 0))

    legs = []
    for leg in best_route.get("legs", []):
        mode = leg.get("mode")  # 'WALK', 'BUS', or 'SUBWAY'/'RAIL'
        route_name = leg.get("route", "")
        from_stop = leg.get("from", {}).get("name", "Start")
        to_stop = leg.get("to", {}).get("name", "End")
        duration = round(leg.get("duration", 0) / 60)

        if mode == "WALK":
            legs.append(f"Walk {round(leg.get('distance', 0))}m ({duration} mins)")
        else:
            legs.append(f"Take {mode} {route_name} from '{from_stop}' to '{to_stop}' ({duration} mins)")

    return {
        "real_commute_mins": total_mins,
        "walk_distance_m": walk_dist,
        "step_by_step": " ➔ ".join(legs),
    }