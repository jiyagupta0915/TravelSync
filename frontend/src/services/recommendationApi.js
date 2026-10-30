import { apiRequest } from "./apiClient";

export function getFeatures() {
  return apiRequest("/api/features");
}

export function searchStartingLocations(query = "", signal) {
  const params = new URLSearchParams({ q: query.trim(), limit: "15" });
  return apiRequest(`/api/start-locations/search?${params.toString()}`, { signal });
}

export function searchDestinations(query = "", signal) {
  const params = new URLSearchParams({ q: query.trim(), limit: "12" });
  return apiRequest(`/api/destinations/search?${params.toString()}`, { signal });
}

export function recommendDestinations(payload, signal) {
  return apiRequest("/api/recommend", { method: "POST", body: payload, signal, fallbackMessage: "The recommendation request could not be completed." });
}

export function getApiHealth() {
  return apiRequest("/api/health");
}
