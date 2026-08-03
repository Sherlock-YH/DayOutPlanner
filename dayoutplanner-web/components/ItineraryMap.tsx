"use client";

import { useEffect, useRef } from "react";
import { Loader } from "@googlemaps/js-api-loader";

interface LocationPoint {
  name: string;
  lat: number;
  lng: number;
}

interface StopPoint {
  stop_number?: number;
  venue_name: string;
  lat: number | null;
  lng: number | null;
}

interface ItineraryMapProps {
  startLocation?: LocationPoint;
  stops: StopPoint[];
  activeStopNumber: number | null;
  onSelectStop: (stopNumber: number) => void;
}

export default function ItineraryMap({
  startLocation,
  stops,
  activeStopNumber,
  onSelectStop,
}: ItineraryMapProps) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const googleMapInstance = useRef<google.maps.Map | null>(null);
  const markersRef = useRef<google.maps.marker.AdvancedMarkerElement[]>([]);
  const polylineRef = useRef<google.maps.Polyline | null>(null);

  useEffect(() => {
    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";

    const loader = new Loader({
      apiKey,
      version: "weekly",
      libraries: ["marker"],
    });

    loader.load().then(async () => {
      if (!mapRef.current) return;

      // Dynamic imports for Google Maps Libraries
      const { Map } = (await google.maps.importLibrary("maps")) as google.maps.MapsLibrary;
      const { AdvancedMarkerElement, PinElement } = (await google.maps.importLibrary(
        "marker"
      )) as google.maps.MarkerLibrary;

      // 1. Initialize Map Instance (mapId is required for AdvancedMarkerElement)
      if (!googleMapInstance.current) {
        googleMapInstance.current = new Map(mapRef.current, {
          center: { lat: 1.3521, lng: 103.8198 }, // Default Singapore Center
          zoom: 12,
          mapId: "DEMO_MAP_ID", // Demo Map ID (or replace with your custom Google Map ID)
          disableDefaultUI: false,
          zoomControl: true,
        });
      }

      const map = googleMapInstance.current;

      // 2. Clear Existing Markers & Polyline
      markersRef.current.forEach((marker) => {
        marker.map = null;
      });
      markersRef.current = [];

      if (polylineRef.current) {
        polylineRef.current.setMap(null);
      }

      const bounds = new google.maps.LatLngBounds();
      const pathCoordinates: google.maps.LatLngLiteral[] = [];

      // 3. Add Start Location Marker
      if (startLocation?.lat && startLocation?.lng) {
        const startPos = { lat: startLocation.lat, lng: startLocation.lng };
        bounds.extend(startPos);
        pathCoordinates.push(startPos);

        // Custom Blue Pin for Starting Location
        const startPin = new PinElement({
          background: "#3b82f6", // Blue
          borderColor: "#1d4ed8",
          glyphColor: "#ffffff",
          glyph: "🚩",
          scale: 1.1,
        });

        const startMarker = new AdvancedMarkerElement({
          map,
          position: startPos,
          title: `Start: ${startLocation.name}`,
          content: startPin.element,
        });

        markersRef.current.push(startMarker);
      }

      // 4. Add Itinerary Stop Markers
      stops.forEach((stop, index) => {
        if (stop.lat && stop.lng) {
          const stopNum = stop.stop_number ?? index + 1;
          const pos = { lat: stop.lat, lng: stop.lng };
          const isSelected = activeStopNumber === stopNum;

          bounds.extend(pos);
          pathCoordinates.push(pos);

          // Custom Emerald Pin with Stop Number
          const pin = new PinElement({
            background: isSelected ? "#10b981" : "#0f766e", // Emerald highlight when selected
            borderColor: isSelected ? "#34d399" : "#115e59",
            glyphColor: "#ffffff",
            glyph: `${stopNum}`,
            scale: isSelected ? 1.3 : 1.0,
          });

          const marker = new AdvancedMarkerElement({
            map,
            position: pos,
            title: `Stop #${stopNum}: ${stop.venue_name}`,
            content: pin.element,
            zIndex: isSelected ? 1000 : stopNum,
          });

          // Click listener to select stop in parent component
          marker.addListener("click", () => {
            onSelectStop(stopNum);
          });

          markersRef.current.push(marker);
        }
      });

      // 5. Draw Connective Route Polyline
      if (pathCoordinates.length > 1) {
        polylineRef.current = new google.maps.Polyline({
          path: pathCoordinates,
          geodesic: true,
          strokeColor: "#10b981", // Emerald green route
          strokeOpacity: 0.8,
          strokeWeight: 4,
          map,
        });
      }

      // 6. Auto-fit Map Zoom to Fit All Markers
      if (!bounds.isEmpty()) {
        map.fitBounds(bounds, {
          top: 60,
          bottom: 60,
          left: 60,
          right: 60,
        });
      }
    });
  }, [startLocation, stops, activeStopNumber, onSelectStop]);

  return (
    <div className="relative w-full h-full min-h-[400px] rounded-2xl overflow-hidden border border-slate-700 shadow-2xl">
      <div ref={mapRef} className="w-full h-full" />
    </div>
  );
}