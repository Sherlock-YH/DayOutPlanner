// components/ItineraryMap.tsx
'use client';

import {
  APIProvider,
  Map,
  AdvancedMarker,
  InfoWindow,
} from '@vis.gl/react-google-maps';

export interface Stop {
  stop_number: number;
  venue_name: string;
  start_time: string;
  end_time: string;
  why_go: string;
  lat: number | null;
  lng: number | null;
}

interface ItineraryMapProps {
  stops: Stop[];
  activeStopNumber: number | null;
  onSelectStop: (stopNumber: number) => void;
}

export default function ItineraryMap({
  stops,
  activeStopNumber,
  onSelectStop,
}: ItineraryMapProps) {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '';

  const validStops = stops.filter(
    (stop): stop is Stop & { lat: number; lng: number } =>
      stop.lat !== null && stop.lng !== null
  );

  const defaultCenter =
    validStops.length > 0
      ? { lat: validStops[0].lat, lng: validStops[0].lng }
      : { lat: 1.3521, lng: 103.8198 };

  return (
    <div className="w-full h-full min-h-[450px] rounded-2xl overflow-hidden shadow-xl border border-slate-700">
      <APIProvider apiKey={apiKey}>
        <Map
          defaultCenter={defaultCenter}
          defaultZoom={12}
          mapId="DEMO_MAP_ID"
          gestureHandling="greedy"
          disableDefaultUI={false}
          className="w-full h-full"
        >
          {validStops.map((stop) => {
            const isSelected = activeStopNumber === stop.stop_number;

            return (
              <div key={`marker-${stop.stop_number}`}>
                {/* Advanced Marker */}
                <AdvancedMarker
                  position={{ lat: stop.lat, lng: stop.lng }}
                  onClick={() => onSelectStop(stop.stop_number)}
                  title={stop.venue_name}
                >
                  <div
                    className={`flex items-center justify-center rounded-full font-bold text-white border-2 shadow-lg transition-all transform cursor-pointer ${
                      isSelected
                        ? 'w-10 h-10 bg-emerald-500 border-white ring-4 ring-emerald-500/40 scale-125 z-50'
                        : 'w-8 h-8 bg-slate-700 border-slate-400 hover:bg-emerald-600 hover:scale-110'
                    }`}
                  >
                    {stop.stop_number}
                  </div>
                </AdvancedMarker>

                {/* InfoWindow Popup on Marker Click */}
                {isSelected && (
                  <InfoWindow
                    position={{ lat: stop.lat, lng: stop.lng }}
                    onCloseClick={() => onSelectStop(0)} // Deselect on close
                  >
                    <div className="p-1.5 max-w-xs text-slate-800">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded">
                          Stop #{stop.stop_number}
                        </span>
                        <span className="text-xs text-slate-500 font-mono">
                          {stop.start_time}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">
                        {stop.venue_name}
                      </h4>
                    </div>
                  </InfoWindow>
                )}
              </div>
            );
          })}
        </Map>
      </APIProvider>
    </div>
  );
}