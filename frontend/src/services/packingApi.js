import { apiRequest } from "./apiClient";

export function getPackingList(tripId) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}/packing-list`, { fallbackMessage: "Could not load the packing list." });
}

export function generatePackingList(tripId, { activities = [], regenerate = false } = {}) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}/packing-list`, { method: "POST", body: { activities, regenerate } });
}

export function updatePackingList(tripId, items) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}/packing-list`, { method: "PATCH", body: { items } });
}

export function setTripDates(tripId, startDate, endDate) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}/packing-list/dates`, { method: "PUT", body: { start_date: startDate, end_date: endDate } });
}
