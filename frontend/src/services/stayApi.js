import { apiRequest } from "./apiClient";

export function getTripStays(tripId) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}/stays`, { fallbackMessage: "Stays could not be loaded." });
}

export function getSavedStays(tripId) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}/stays/saved`);
}

export function saveStay(tripId, stayKey) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}/stays/saved`, { method: "POST", body: { stay_key: stayKey } });
}

export function removeSavedStay(tripId, stayKey) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}/stays/saved/${encodeURIComponent(stayKey)}`, { method: "DELETE" });
}
