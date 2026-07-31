from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# 1. Pydantic Schemas (The Data Contract)
# Simplified Pydantic schema for the LLM
class ItineraryStop(BaseModel):
    venue_name: str
    category: str
    stay_duration_minutes: int
    why_go: str


class SingaporeItinerary(BaseModel):
    title: str = Field(description="Catchy title for the day's itinerary")
    target_audience: str = Field(description="Who this plan is best for (e.g., Foodies, Nature lovers, Families)")
    day_type: str = Field(description="Whether this is tailored for a Weekday or Weekend")
    stops: List[ItineraryStop] = Field(description="List of sequential stops for the day")


# 2. OpenAI Client Initialization
client = OpenAI()


def generate_singapore_itinerary(prompt: str) -> SingaporeItinerary:
    """Calls OpenAI LLM and forces response conformity to the SingaporeItinerary schema."""
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert local Singapore tour guide and urban planner. Provide realistic, "
                           "geographically logical itineraries featuring actual MRT lines, landmarks, and accurate "
                           "coordinates. Ensure venues are geographically ordered from North to South or West to East "
                           "to minimize overall travel time. Ensure the travel time from one stop to another is not "
                           "exceeding 40 minutes"
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
    # Quick standalone test for LLM generation
    test_prompt = "Generate a relaxed Saturday itinerary in Singapore focusing on nature and local hawker food."
    result = generate_singapore_itinerary(test_prompt)
    print(f"Generated Itinerary: {result.title} with {len(result.stops)} stops.")