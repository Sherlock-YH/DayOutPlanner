from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI


# 1. Define the Pydantic Schema (The Data Contract)
class ItineraryStop(BaseModel):
    stop_number: int = Field(description="The sequential order of the stop (1, 2, 3...)")
    venue_name: str = Field(
        description="Name of the specific place in Singapore (e.g., Lau Pa Sat, Tiong Bahru Bakery)")
    category: str = Field(description="Category like Food, Nature, Culture, Shopping, or Entertainment")
    estimated_duration_mins: int = Field(description="Estimated time spent here in minutes")
    lat: float = Field(description="Latitude coordinate of the venue")
    lng: float = Field(description="Longitude coordinate of the venue")
    commute_tips_from_previous: Optional[str] = Field(
        description="How to get here from the previous stop via MRT/Bus/Walking")
    reason: str = Field(description="Why this place fits the user's theme/request")


class SingaporeItinerary(BaseModel):
    title: str = Field(description="Catchy title for the day's itinerary")
    target_audience: str = Field(description="Who this plan is best for (e.g., Foodies, Nature lovers, Families)")
    day_type: str = Field(description="Whether this is tailored for a Weekday or Weekend")
    stops: List[ItineraryStop] = Field(description="List of sequential stops for the day")


# 2. Initialize OpenAI client
client = OpenAI()


def generate_singapore_itinerary(prompt: str) -> SingaporeItinerary:
    """Calls the LLM and forces response conformity to the SingaporeItinerary schema."""
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert local Singapore tour guide and urban planner. Provide realistic, geographically logical itineraries featuring actual MRT lines, landmarks, and accurate coordinates."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format=SingaporeItinerary,
    )
    return completion.choices[0].message.parsed


if __name__ == "__main__":
    # Test the script with a sample prompt
    user_prompt = "Generate a relaxed Saturday itinerary in Singapore focusing on nature and local hawker food."
    print(f"Generating plan for: '{user_prompt}'...\n" + "-" * 50)

    itinerary = generate_singapore_itinerary(user_prompt)

    print(f"📌 {itinerary.title}")
    print(f"👥 Target: {itinerary.target_audience} | 📅 Type: {itinerary.day_type}\n")

    for stop in itinerary.stops:
        print(f"Stop {stop.stop_number}: {stop.venue_name} [{stop.category}]")
        print(f"⏱️ Duration: {stop.estimated_duration_mins} mins")
        if stop.commute_tips_from_previous:
            print(f"🚇 Commute: {stop.commute_tips_from_previous}")
        print(f"💡 Why go: {stop.reason}")
        print(f"📍 Coords: ({stop.lat}, {stop.lng})\n")