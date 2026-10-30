import { apiRequest } from "./apiClient";

// Permanently deletes a trip together with its packing list, saved stays and bookings.
export function deleteTrip(tripId) {
  return apiRequest(`/api/trips/${encodeURIComponent(tripId)}`, { method: "DELETE", fallbackMessage: "The trip could not be deleted." });
}
