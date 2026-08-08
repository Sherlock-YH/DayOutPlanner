"use client";

import { useState, useEffect } from "react";
import ItineraryMap from "@/components/ItineraryMap";
import LocationAutocomplete from "@/components/LocationAutocomplete";

const API_BASE = "https://dayoutplanner.up.railway.app";

// Generate 30-minute interval options
const TIME_OPTIONS = (() => {
  const options = [];
  for (let hour = 0; hour < 24; hour++) {
    for (let min = 0; min < 60; min += 30) {
      const hStr = hour.toString().padStart(2, "0");
      const mStr = min.toString().padStart(2, "0");
      const value = `${hStr}:${mStr}`;

      const period = hour >= 12 ? "PM" : "AM";
      const displayHour = hour % 12 === 0 ? 12 : hour % 12;
      const label = `${displayHour}:${mStr} ${period}`;

      options.push({ value, label });
    }
  }
  return options;
})();

const QUICK_CHIP_GROUPS = [
  {
    category: "Pace",
    chips: ["Relaxed (1-2 stops)", "Moderate(3-4)", "Packed (5+ stops)"],
  },
  {
    category: "Diet",
    chips: ["Halal", "Vegetarian", "Hawker Only", "Meat Lover", "No Food"],
  },
  {
    category: "Style",
    chips: ["Air-Conditioned / Indoor", "Outdoor & Nature", "Family Friendly", "Pet Friendly"],
  },
];

export default function Home() {
  // Auth States
  const [token, setToken] = useState<string | null>(null);
  const [isSignup, setIsSignup] = useState(false);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);

  // App Input States
  const [prompt, setPrompt] = useState("");
  const [startLocation, setStartLocation] = useState("");
  const [startTime, setStartTime] = useState("10:00");
  const [selectedChips, setSelectedChips] = useState<string[]>([]);

  // UI & Data States
  const [loading, setLoading] = useState(false);
  const [itinerary, setItinerary] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeStopNumber, setActiveStopNumber] = useState<number | null>(null);

  // Load token on client mount
  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    if (savedToken) setToken(savedToken);
  }, []);

  // Handle Authentication (Login / Signup)
  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);

    const endpoint = isSignup ? "/api/auth/signup" : "/api/auth/login";
    let headers: Record<string, string> = {};
    let body: any;

    if (isSignup) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify({ email: authEmail, password: authPassword });
    } else {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
      const formData = new URLSearchParams();
      formData.append("username", authEmail);
      formData.append("password", authPassword);
      body = formData.toString();
    }

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers,
        body,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Authentication failed");

      if (isSignup) {
        alert("Account created successfully! Please log in.");
        setIsSignup(false);
      } else {
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
      }
    } catch (err: any) {
      setAuthError(err.message || "An error occurred during authentication.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setItinerary(null);
  };

  const toggleChip = (chip: string) => {
    setSelectedChips((prev) =>
      prev.includes(chip) ? prev.filter((c) => c !== chip) : [...prev, chip]
    );
  };

  const handleSelectStop = (stopNumber: number) => {
    setActiveStopNumber(stopNumber);
    if (!stopNumber) return;

    const cardElement = document.getElementById(`stop-card-${stopNumber}`);
    if (cardElement) {
      cardElement.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    const fullPromptParts = [prompt.trim(), ...selectedChips].filter(Boolean);
    const finalPrompt = fullPromptParts.join(", ");

    if (!finalPrompt.trim()) return;

    setLoading(true);
    setError(null);
    setActiveStopNumber(null);

    try {
      const response = await fetch(`${API_BASE}/api/plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`, // Passes the user JWT token
        },
        body: JSON.stringify({
          prompt: finalPrompt,
          start_location: startLocation.trim(),
          start_time: startTime,
        }),
      });

      if (response.status === 401) {
        // Token expired or invalid
        handleLogout();
        throw new Error("Session expired. Please log in again.");
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Error ${response.status}`);
      }

      const data = await response.json();
      setItinerary(data);
    } catch (err: any) {
      setError(err.message || "Unable to connect to planner backend.");
    } finally {
      setLoading(false);
    }
  };

  // ==========================================
  // VIEW 1: AUTHENTICATION SCREEN (If not logged in)
  // ==========================================
  if (!token) {
    return (
      <main className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-slate-800/90 border border-slate-700 rounded-2xl p-8 space-y-6 shadow-2xl">
          <div className="text-center space-y-2">
            <h1 className="text-3xl font-extrabold tracking-tight text-emerald-400">
              🇸🇬 One Day Out Planner
            </h1>
            <p className="text-slate-400 text-sm">
              {isSignup ? "Create an account to start planning" : "Log in to access your itinerary engine"}
            </p>
          </div>

          {authError && (
            <div className="p-3 bg-red-900/40 border border-red-700 rounded-xl text-red-200 text-xs">
              ⚠️ {authError}
            </div>
          )}

          <form onSubmit={handleAuthSubmit} className="space-y-4">
            <div className="space-y-1.5 text-left">
              <label className="text-xs font-semibold text-slate-400">Email Address</label>
              <input
                type="email"
                required
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              />
            </div>

            <div className="space-y-1.5 text-left">
              <label className="text-xs font-semibold text-slate-400">Password</label>
              <input
                type="password"
                required
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              />
            </div>

            <button
              type="submit"
              className="w-full bg-emerald-500 hover:bg-emerald-600 font-bold text-slate-950 py-3 rounded-xl transition-all text-sm cursor-pointer shadow-lg shadow-emerald-500/10"
            >
              {isSignup ? "Sign Up" : "Log In"}
            </button>
          </form>

          <div className="text-center pt-2">
            <button
              onClick={() => {
                setIsSignup(!isSignup);
                setAuthError(null);
              }}
              className="text-xs text-slate-400 hover:text-emerald-400 transition-colors cursor-pointer"
            >
              {isSignup ? "Already have an account? Log in" : "Need an account? Sign up"}
            </button>
          </div>
        </div>
      </main>
    );
  }

  // ==========================================
  // VIEW 2: MAIN PLANNER DASHBOARD (If logged in)
  // ==========================================
  return (
    <main className="min-h-screen bg-slate-900 text-slate-100 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header & Logout */}
        <header className="flex flex-col sm:flex-row items-center justify-between border-b border-slate-800 pb-4 gap-4">
          <div className="text-center sm:text-left space-y-1">
            <h1 className="text-3xl font-extrabold tracking-tight text-emerald-400">
              🇸🇬 One Day Out Planner
            </h1>
            <p className="text-slate-400 text-sm">
              AI Travel Orchestrator powered by GPT-4o & Google Maps
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="text-xs px-4 py-2 border border-slate-700 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition cursor-pointer"
          >
            Log Out
          </button>
        </header>

        {/* Input Form */}
        <form
          onSubmit={handleGenerate}
          className="bg-slate-800/80 border border-slate-700 rounded-2xl p-5 space-y-5 shadow-xl max-w-3xl mx-auto"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Start Location Input */}
            <div className="space-y-1.5 text-left">
              <label className="text-xs font-semibold text-slate-400">
                📍 Start Location
              </label>
              <LocationAutocomplete
                value={startLocation}
                onChange={setStartLocation}
                placeholder="e.g. Marina Bay Sands, Changi Airport..."
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              />
            </div>

            {/* Start Time Dropdown */}
            <div className="space-y-1.5 text-left">
              <label className="text-xs font-semibold text-slate-400">
                ⏰ Start Time
              </label>
              <div className="relative">
                <select
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:ring-2 focus:ring-emerald-500 outline-none appearance-none cursor-pointer"
                >
                  {TIME_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 text-xs">
                  ▼
                </div>
              </div>
            </div>
          </div>

          {/* Quick-Chips */}
          <div className="space-y-3 pt-2 border-t border-slate-700/60 text-left">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">
                🎛️ Quick Filters & Pace Presets
              </span>
              {selectedChips.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSelectedChips([])}
                  className="text-xs text-slate-400 hover:text-emerald-400 transition-colors cursor-pointer"
                >
                  Clear filters ({selectedChips.length})
                </button>
              )}
            </div>

            <div className="space-y-2">
              {QUICK_CHIP_GROUPS.map((group) => (
                <div key={group.category} className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-medium text-slate-400 min-w-[45px]">
                    {group.category}:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {group.chips.map((chip) => {
                      const isSelected = selectedChips.includes(chip);
                      return (
                        <button
                          key={chip}
                          type="button"
                          onClick={() => toggleChip(chip)}
                          className={`text-xs px-3 py-1.5 rounded-lg border transition-all font-medium cursor-pointer ${
                            isSelected
                              ? "bg-emerald-500/20 border-emerald-500 text-emerald-300 ring-1 ring-emerald-500/50"
                              : "bg-slate-900/60 border-slate-700 text-slate-300 hover:border-slate-500 hover:bg-slate-800"
                          }`}
                        >
                          {isSelected && <span className="mr-1 text-emerald-400">✓</span>}
                          {chip}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Prompt Input */}
          <div className="space-y-1.5 text-left pt-1">
            <label className="text-xs font-semibold text-slate-400">
              🎯 Trip Theme & Preferences
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. Family-friendly indoor tour with local coffee..."
                className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              />
              <button
                type="submit"
                disabled={loading}
                className="bg-emerald-500 hover:bg-emerald-600 font-bold text-slate-950 px-6 py-3 rounded-xl transition-all disabled:opacity-50 text-sm whitespace-nowrap cursor-pointer shadow-lg shadow-emerald-500/10"
              >
                {loading ? "Planning..." : "Generate Plan"}
              </button>
            </div>
          </div>
        </form>

        {error && (
          <div className="p-4 bg-red-900/40 border border-red-700 rounded-xl text-red-200 text-sm max-w-2xl mx-auto text-left">
            ⚠️ {error}
          </div>
        )}

        {/* Split-Screen View */}
        {itinerary && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start pt-4 text-left">
            {/* Left Column: Timeline Cards */}
            <div className="lg:col-span-7 space-y-6">
              <div className="bg-slate-800/60 border border-slate-700 rounded-2xl p-6 space-y-2">
                <h2 className="text-2xl font-bold text-white">
                  {itinerary.title || "Your Itinerary Plan"}
                </h2>
                <p className="text-slate-300 text-sm leading-relaxed">
                  {itinerary.summary}
                </p>
              </div>

              <div className="relative pl-6 border-l-2 border-emerald-500/30 space-y-8">
                {/* START LOCATION */}
                <div className="relative space-y-4">
                  <div className="absolute -left-[31px] top-4 w-4 h-4 rounded-full bg-blue-500 ring-4 ring-slate-900" />

                  <div className="bg-slate-800/90 border border-blue-500/40 rounded-xl p-4 space-y-1">
                    <div className="flex items-center justify-between text-xs font-semibold text-blue-400">
                      <span>🚩 STARTING POINT</span>
                      <span className="font-mono text-slate-400">
                        ⏰ Depart at {itinerary.start_time}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-white">
                      {itinerary.start_location}
                    </h3>
                  </div>

                  {itinerary.initial_transit && (
                    <div className="bg-slate-800/40 border border-slate-700/60 rounded-lg p-4 ml-2 text-xs space-y-2 text-slate-300">
                      <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                        <span>🚍 COMMUTE TO STOP #1</span>
                        <span>({itinerary.initial_transit.commute_mins} mins)</span>
                      </div>
                      <p className="font-mono whitespace-pre-line text-slate-300 leading-relaxed">
                        {itinerary.initial_transit.step_by_step}
                      </p>
                    </div>
                  )}
                </div>

                {/* ITINERARY STOPS */}
                {(itinerary.stops || []).map((stop: any, index: number) => {
                  const stopNum = stop.stop_number ?? index + 1;
                  const isSelected = activeStopNumber === stopNum;

                  return (
                    <div key={`stop-${stopNum}-${index}`} className="relative space-y-4">
                      <div
                        className={`absolute -left-[31px] top-4 w-4 h-4 rounded-full ring-4 transition-all ${
                          isSelected
                            ? "bg-emerald-400 ring-emerald-400/50 scale-125"
                            : "bg-emerald-500 ring-slate-900"
                        }`}
                      />

                      <div
                        id={`stop-card-${stopNum}`}
                        onClick={() => handleSelectStop(stopNum)}
                        className={`cursor-pointer transition-all duration-300 rounded-xl p-5 space-y-3 shadow-lg border ${
                          isSelected
                            ? "bg-slate-800 ring-2 ring-emerald-400 border-emerald-500/80 shadow-emerald-500/10 scale-[1.01]"
                            : "bg-slate-800 border-slate-700 hover:border-slate-500"
                        }`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span
                            className={`text-xs font-semibold uppercase tracking-wider px-2.5 py-1 rounded-md border transition-colors ${
                              isSelected
                                ? "bg-emerald-500 text-slate-950 border-emerald-400 font-bold"
                                : "text-emerald-400 bg-emerald-950/60 border-emerald-800/50"
                            }`}
                          >
                            Stop #{stopNum}
                          </span>
                          <span className="text-xs font-mono text-slate-400">
                            ⏰ {stop.start_time} – {stop.end_time} ({stop.duration_mins || stop.stay_duration_mins} mins)
                          </span>
                        </div>

                        <h3 className="text-lg font-bold text-white">{stop.venue_name}</h3>
                        <p className="text-slate-300 text-sm leading-relaxed">{stop.why_go}</p>
                      </div>

                      {stop.transit_to_next && (
                        <div className="bg-slate-800/40 border border-slate-700/60 rounded-lg p-4 ml-2 text-xs space-y-2 text-slate-300">
                          <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                            <span>🚍 COMMUTE</span>
                            <span>({stop.transit_to_next.commute_mins} mins)</span>
                          </div>
                          <p className="font-mono whitespace-pre-line text-slate-300 leading-relaxed">
                            {stop.transit_to_next.step_by_step}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right Column: Google Map */}
            <div className="lg:col-span-5 lg:sticky lg:top-8 h-[500px] lg:h-[calc(100vh-4rem)]">
              <ItineraryMap
                startLocation={
                  itinerary?.initial_transit?.start_coords
                    ? {
                        name: itinerary.start_location,
                        lat: itinerary.initial_transit.start_coords.lat,
                        lng: itinerary.initial_transit.start_coords.lng,
                      }
                    : undefined
                }
                stops={itinerary?.stops || []}
                activeStopNumber={activeStopNumber}
                onSelectStop={handleSelectStop}
              />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}