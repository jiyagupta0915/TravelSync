import { apiRequest } from "./apiClient";

// Destination centre, top-5 places (with coordinates) and shortlisted stays for one trip.
export function getTripMap(tripId) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}/map`, { fallbackMessage: "The map could not be loaded." });
}

// Driving distance and time from the user's location to the trip's places.
// Resolves with { source: "geoapify" | "cache" | "unavailable", distances: { [pinId]: { km, minutes } } }.
export function getDriveDistances(tripId, position) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}/map/distances`, {
    method: "POST",
    body: { lat: position.lat, lon: position.lon },
    fallbackMessage: "Driving distances could not be loaded.",
  });
}