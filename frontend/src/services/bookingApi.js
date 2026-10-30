import { apiRequest } from "./apiClient";

export const listBookings = (tripId) =>
  apiRequest(`/api/bookings${tripId ? `?trip_id=${encodeURIComponent(tripId)}` : ""}`, { fallbackMessage: "Your bookings could not be loaded." });
export const createBooking = (payload) => apiRequest("/api/bookings", { method: "POST", body: payload });
export const updateBooking = (id, payload) => apiRequest(`/api/bookings/${encodeURIComponent(id)}`, { method: "PUT", body: payload });
export const deleteBooking = (id) => apiRequest(`/api/bookings/${encodeURIComponent(id)}`, { method: "DELETE" });
