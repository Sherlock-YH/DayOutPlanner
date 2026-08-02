// components/ItineraryMap.tsx
"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  GoogleMap,
  useJsApiLoader,
  MarkerF,
  PolylineF,
  InfoWindowF,
} from "@react-google-maps/api";

interface Stop {
  stop_number: number;
  venue_name: str;
  lat: number | null;
  lng: number | null;
  start_time?: string;
  end_time?: string;
}

interface StartLocationInfo {
  name: string;
  lat: number;
  lng: number;
}

interface ItineraryMapProps {
  startLocation?: StartLocationInfo;
  stops: Stop[];
  activeStopNumber: number | null;
  onSelectStop: (stopNumber: number) => void;
}

const mapContainerStyle = {
  width: "100%",
  height: "100%",
  borderRadius: "1rem",
};

const defaultCenter = {
  lat: 1.3521, // Singapore default
  lng: 103.8198,
};

const darkMapStyle = [
  { elementType: "geometry", stylers: [{ color: "#1e293b" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#0f172a" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#94a3b8" }] },
  {
    featureType: "administrative.locality",
    elementType: "labels.text.fill",
    stylers: [{ color: "#cbd5e1" }],
  },
  {
    featureType: "poi",
    elementType: "labels.text.fill",
    stylers: [{ color: "#64748b" }],
  },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#334155" }],
  },
  {
    featureType: "road.highway",
    elementType: "geometry",
    stylers: [{ color: "#475569" }],
  },
  {
    featureType: "transit",
    elementType: "geometry",
    stylers: [{ color: "#1e293b" }],
  },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#0f172a" }],
  },
];

export default function ItineraryMap({
  startLocation,
  stops,
  activeStopNumber,
  onSelectStop,
}: ItineraryMapProps) {
  const mapRef = useRef<google.maps.Map | null>(null);
  const [selectedMarker, setSelectedMarker] = useState<Stop | StartLocationInfo | null>(null);

  const { isLoaded } = useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "",
  });

  const validStops = stops.filter(
    (stop): stop is Stop & { lat: number; lng: number } =>
      stop.lat !== null && stop.lng !== null
  );

  // Auto-fit map bounds to contain Start Location and all valid Stops
  const fitMapBounds = useCallback(() => {
    if (!mapRef.current || (!startLocation && validStops.length === 0)) return;

    const bounds = new window.google.maps.LatLngBounds();

    if (startLocation?.lat && startLocation?.lng) {
      bounds.extend({ lat: startLocation.lat, lng: startLocation.lng });
    }

    validStops.forEach((stop) => {
      bounds.extend({ lat: stop.lat, lng: stop.lng });
    });

    mapRef.current.fitBounds(bounds, {
      top: 60,
      bottom: 60,
      left: 60,
      right: 60,
    });
  }, [startLocation, validStops]);

  const onLoad = useCallback(
    (map: google.maps.Map) => {
      mapRef.current = map;
      fitMapBounds();
    },
    [fitMapBounds]
  );

  const onUnmount = useCallback(() => {
    mapRef.current = null;
  }, []);

  useEffect(() => {
    fitMapBounds();
  }, [stops, startLocation, fitMapBounds]);

  if (!isLoaded) {
    return (
      <div className="w-full h-full bg-slate-800/60 rounded-2xl flex items-center justify-center text-slate-400 text-sm border border-slate-700">
        Loading Map...
      </div>
    );
  }

  // Construct full route coordinate list (Start -> Stop 1 -> Stop 2 ...)
  const pathCoordinates = [
    ...(startLocation ? [{ lat: startLocation.lat, lng: startLocation.lng }] : []),
    ...validStops.map((s) => ({ lat: s.lat, lng: s.lng })),
  ];

  // Helper for Start Location custom SVG Marker Icon
  const createStartIcon = (): google.maps.Icon => ({
    url:
      "data:image/svg+xml;charset=UTF-8," +
      encodeURIComponent(`
      <svg xmlns="http://www.w3.org/2000/svg" width="38" height="50" viewBox="0 0 38 50">
        <path fill="#2563EB" stroke="#FFFFFF" stroke-width="2" d="M19 0C8.507 0 0 8.507 0 19c0 14.25 19 31 19 31s19-16.75 19-31C38 8.507 29.493 0 19 0z"/>
        <circle cx="19" cy="19" r="12" fill="#1E3A8A"/>
        <text x="19" y="24" font-size="14" font-family="sans-serif" text-anchor="middle">🚩</text>
      </svg>
    `),
    scaledSize: new window.google.maps.Size(38, 50),
    anchor: new window.google.maps.Point(19, 50),
  });

  // Helper for Stop Number custom SVG Marker Icon
  const createStopIcon = (
    stopNum: number,
    isSelected: boolean
  ): google.maps.Icon => {
    const bgColor = isSelected ? "#10B981" : "#059669";
    const strokeColor = isSelected ? "#A7F3D0" : "#FFFFFF";
    const scale = isSelected ? 1.2 : 1.0;
    const width = 36 * scale;
    const height = 48 * scale;

    return {
      url:
        "data:image/svg+xml;charset=UTF-8," +
        encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 36 48">
          <path fill="${bgColor}" stroke="${strokeColor}" stroke-width="${
          isSelected ? "3" : "1.5"
        }" d="M18 0C8.059 0 0 8.059 0 18c0 13.5 18 30 18 30s18-16.5 18-30C36 8.059 27.941 0 18 0z"/>
          <circle cx="18" cy="18" r="11" fill="#0F172A"/>
          <text x="18" y="23" font-size="13" font-weight="bold" font-family="sans-serif" text-anchor="middle" fill="#10B981">${stopNum}</text>
        </svg>
      `),
      scaledSize: new window.google.maps.Size(width, height),
      anchor: new window.google.maps.Point(width / 2, height),
    };
  };

  return (
    <GoogleMap
      mapContainerStyle={mapContainerStyle}
      center={defaultCenter}
      zoom={12}
      onLoad={onLoad}
      onUnmount={onUnmount}
      options={{
        styles: darkMapStyle,
        disableDefaultUI: false,
        zoomControl: true,
      }}
    >
      {/* Route Connecting Line */}
      {pathCoordinates.length > 1 && (
        <PolylineF
          path={pathCoordinates}
          options={{
            strokeColor: "#10B981",
            strokeOpacity: 0.8,
            strokeWeight: 4,
          }}
        />
      )}

      {/* 🚩 START LOCATION MARKER */}
      {startLocation && startLocation.lat && startLocation.lng && (
        <MarkerF
          position={{ lat: startLocation.lat, lng: startLocation.lng }}
          icon={createStartIcon()}
          onClick={() => setSelectedMarker(startLocation)}
          title={`Start: ${startLocation.name}`}
        />
      )}

      {/* 📍 ITINERARY STOP MARKERS */}
      {validStops.map((stop) => {
        const isSelected = activeStopNumber === stop.stop_number;

        return (
          <MarkerF
            key={`marker-${stop.stop_number}`}
            position={{ lat: stop.lat, lng: stop.lng }}
            icon={createStopIcon(stop.stop_number, isSelected)}
            onClick={() => {
              onSelectStop(stop.stop_number);
              setSelectedMarker(stop);
            }}
            title={stop.venue_name}
            zIndex={isSelected ? 999 : stop.stop_number}
          />
        );
      })}

      {/* ℹ️ INFO WINDOW ON MARKER CLICK */}
      {selectedMarker && (
        <InfoWindowF
          position={{
            lat: selectedMarker.lat!,
            lng: selectedMarker.lng!,
          }}
          onCloseClick={() => setSelectedMarker(null)}
        >
          <div className="p-2 text-slate-900 max-w-xs space-y-1">
            {"stop_number" in selectedMarker ? (
              <>
                <div className="text-xs font-bold text-emerald-600 uppercase">
                  Stop #{selectedMarker.stop_number}
                </div>
                <div className="font-bold text-sm text-slate-900">
                  {selectedMarker.venue_name}
                </div>
                {selectedMarker.start_time && (
                  <div className="text-xs text-slate-500">
                    ⏰ {selectedMarker.start_time} – {selectedMarker.end_time}
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="text-xs font-bold text-blue-600 uppercase">
                  🚩 Starting Location
                </div>
                <div className="font-bold text-sm text-slate-900">
                  {selectedMarker.name}
                </div>
              </>
            )}
          </div>
        </InfoWindowF>
      )}
    </GoogleMap>
  );
}