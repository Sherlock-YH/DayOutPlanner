"use client";

import { useEffect, useRef } from "react";
import { Loader } from "@googlemaps/js-api-loader";

interface LocationAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export default function LocationAutocomplete({
  value,
  onChange,
  placeholder = "e.g. Marina Bay Sands or Changi Airport",
  className = "",
}: LocationAutocompleteProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null);

      useEffect(() => {
      const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
      if (!apiKey) return;

      const loader = new Loader({
        apiKey,
        version: "weekly",
        libraries: ["places", "marker"], // 👈 Updated to include both
      });

    loader.load().then(async () => {
      if (!inputRef.current || autocompleteRef.current) return;

      const { Autocomplete } = (await google.maps.importLibrary(
        "places"
      )) as google.maps.PlacesLibrary;

      // Initialize Places Autocomplete attached directly to our HTML input element
      const autocomplete = new Autocomplete(inputRef.current, {
        componentRestrictions: { country: "sg" },
        fields: ["formatted_address", "name", "geometry"],
      });

      autocomplete.addListener("place_changed", () => {
        const place = autocomplete.getPlace();
        const selectedLocation = place.name || place.formatted_address || "";
        if (selectedLocation) {
          onChange(selectedLocation);
        }
      });

      autocompleteRef.current = autocomplete;
    });
  }, [onChange]);

  return (
    <input
      ref={inputRef}
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={className}
    />
  );
}