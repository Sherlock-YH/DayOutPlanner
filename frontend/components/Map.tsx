// components/Map.tsx
"use client";

import { useMemo, useCallback, useRef } from "react";
import { GoogleMap, useJsApiLoader, MarkerF, PolylineF } from "@react-google-maps/api";
import { ItineraryStop } from "@/types/itinerary";

const containerStyle = {
  width: "100%",
  height: "100%",
  borderRadius: "1rem",
};

const defaultCenter = { lat: 1.3521, lng: 103.8198 }; // Singapore Center

// Dark mode map theme styling
const darkMapStyles = [
  { elementType: "geometry", stylers: [{ color: "#1e293b" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#0f172a" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#94a3b8" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#334155" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#0f172a" }] },
];

export default function ItineraryMap({ stops }: { stops: ItineraryStop[] }) {
  const { isLoaded } = useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "",
  });

  const mapRef = useRef<google.maps.Map | null>(null);

  // Filter stops with valid lat/lng
  const validStops = useMemo(() => {
    return stops.filter((s): s is ItineraryStop & { lat: number; lng: number } =>
      typeof s.lat === "number" && typeof s.lng === "number"
    );
  }, [stops]);

  // Coordinates array for route polyline
  const polylinePath = useMemo(() => {
    return validStops.map((s) => ({ lat: s.lat, lng: s.lng }));
  }, [validStops]);

  // Automatically adjust zoom and bounds to fit all markers
  const onLoad = useCallback((map: google.maps.Map) => {
    mapRef.current = map;
    if (validStops.length > 0) {
      const bounds = new window.google.maps.LatLngBounds();
      validStops.forEach((s) => bounds.extend({ lat: s.lat, lng: s.lng }));
      map.fitBounds(bounds, { top: 60, right: 60, bottom: 60, left: 60 });
    }
  }, [validStops]);

  if (!isLoaded) {
    return (
      <div className="w-full h-full min-h-[400px] bg-slate-800/60 border border-slate-700 rounded-2xl animate-pulse flex items-center justify-center text-slate-400 text-sm">
        🗺️ Loading Google Map Engine...
      </div>
    );
  }

  return (
    <GoogleMap
      mapContainerStyle={containerStyle}
      center={defaultCenter}
      zoom={12}
      onLoad={onLoad}
      options={{
        disableDefaultUI: false,
        zoomControl: true,
        styles: darkMapStyles,
      }}
    >
      {/* Numbered Stop Markers */}
      {validStops.map((stop, index) => (
        <MarkerF
          key={`marker-${stop.stop_number || index}`}
          position={{ lat: stop.lat, lng: stop.lng }}
          label={{
            text: `${stop.stop_number || index + 1}`,
            color: "#ffffff",
            fontWeight: "bold",
            fontSize: "13px",
          }}
          title={stop.venue_name}
        />
      ))}

      {/* Emerald Route Polyline connecting stops */}
      {polylinePath.length > 1 && (
        <PolylineF
          path={polylinePath}
          options={{
            strokeColor: "#10b981", // Emerald-500
            strokeOpacity: 0.8,
            strokeWeight: 4,
          }}
        />
      )}
    </GoogleMap>
  );
}