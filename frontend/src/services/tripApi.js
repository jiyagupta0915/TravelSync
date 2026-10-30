import { apiRequest } from "./apiClient";

export function getTrips() {
  return apiRequest("/api/trips", { fallbackMessage: "Your trips could not be loaded." });
}

export function getTrip(tripId) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}`, { fallbackMessage: "This trip could not be loaded." });
}

export function createTrip(payload) {
  return apiRequest("/api/trips", { method: "POST", body: payload, fallbackMessage: "The trip could not be saved." });
}
