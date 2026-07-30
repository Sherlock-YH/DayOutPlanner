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
    """Queries SLA OneMap Routing API using exact planned departure timestamp."""
    url = "https://www.onemap.gov.sg/api/public/routingsvc/route"

    date_str = departure_datetime.strftime("%m-%d-%Y")
    time_str = departure_datetime.strftime("%H:%M:%S")

    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "start": f"{start_lat},{start_lng}",
        "end": f"{end_lat},{end_lng}",
        "routeType": "pt",
        "mode": "TRANSIT",
        "date": date_str,
        "time": time_str,
        "maxWalkDistance": "2000",  # Increased to allow bus access/egress walks
        "numItineraries": "1",
    }

    response = requests.get(url, headers=headers, params=params)

    # Catch 404 (e.g. Lazarus Island, Pulau Ubin where no bus/MRT exists)
    if response.status_code == 404:
        return {"error": "NO_PUBLIC_TRANSIT_COVERAGE"}

    response.raise_for_status()
    return response.json()


def search_onemap_coords(venue_name: str) -> tuple[float, float] | None:
    """
    Searches SLA OneMap Elastic Search API for a venue name
    and returns its exact verified (latitude, longitude).
    """
    url = "https://www.onemap.gov.sg/api/common/elastic/search"
    params = {
        "searchVal": venue_name,
        "returnGeom": "Y",
        "getAddrDetails": "Y",
        "pageNum": "1"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if results:
            # First result is usually the best match
            best_match = results[0]
            lat = float(best_match["LATITUDE"])
            lng = float(best_match["LONGITUDE"])
            return lat, lng

    except Exception as e:
        print(f"⚠️ Geocoding failed for '{venue_name}': {e}")

    return None


def parse_route_summary(
    route_data: dict,
    start_venue: str = "",
    end_venue: str = ""
) -> dict:
    if route_data.get("error") == "NO_PUBLIC_TRANSIT_COVERAGE":
        return {
            "real_commute_mins": 45,
            "walk_distance_m": 0,
            "step_by_step": "⛵ Offshore Ferry Transfer required",
            "is_offshore": True,
        }

    plan = route_data.get("plan", {})
    itineraries = plan.get("itineraries", [])

    if not itineraries:
        return {
            "real_commute_mins": 10,
            "walk_distance_m": 0,
            "step_by_step": "🚖 Recommended: Short Taxi/Grab ride (~$6-8 SGD)",
            "is_offshore": False,
        }

    best_route = itineraries[0]
    total_mins = round(best_route.get("duration", 0) / 60)
    walk_dist = round(best_route.get("walkDistance", 0))

    legs = best_route.get("legs", [])
    is_pure_walk = all(leg.get("mode") == "WALK" for leg in legs)

    # 🚨 PURE WALK DETECTOR: If route is 100% walking and > 800m
    if is_pure_walk and walk_dist > 800:
        dist_km = walk_dist / 1000.0

        # 1. Dynamic Drive Time: ~30 km/h average city speed (500m/min) + 3-min pickup/traffic buffer
        drive_mins = max(5, round((dist_km / 0.5) + 3))

        # 2. Dynamic Fare Formula (Base ~$4.50 + ~$0.90/km)
        estimated_base = 4.50 + (dist_km * 0.90)

        # Standard SG Taxi/Grab minimum fare is ~$6.00
        min_fare = max(10, round(estimated_base))
        max_fare = round(min_fare * 1.35)  # 35% buffer for peak surcharges / dynamic pricing

        return {
            "real_commute_mins": drive_mins,
            "walk_distance_m": walk_dist,
            "step_by_step": (
                f"🚖 Recommended: ~{drive_mins} min Taxi/Grab (~${min_fare}-${max_fare} SGD) "
                f"| 🚶 Optional Walk: {walk_dist}m ({total_mins} mins)"
            ),
            "is_offshore": False,
        }

    formatted_legs = []
    for leg in legs:
        mode = leg.get("mode")
        route_name = leg.get("route", "")
        from_stop = leg.get("from", {}).get("name", "Start")
        to_stop = leg.get("to", {}).get("name", "End")
        duration = round(leg.get("duration", 0) / 60)
        leg_dist = round(leg.get("distance", 0))

        if mode == "WALK":
            formatted_legs.append(f"Walk {leg_dist}m ({duration} mins)")
        else:
            formatted_legs.append(f"Take {mode} {route_name} from '{from_stop}' to '{to_stop}' ({duration} mins)")

    return {
        "real_commute_mins": total_mins,
        "walk_distance_m": walk_dist,
        "step_by_step": " ➔ ".join(formatted_legs),
        "is_offshore": False,
    }