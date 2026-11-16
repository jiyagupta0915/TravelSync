import { apiRequest } from "./apiClient";

const b = (id) => `/api/bookings/${encodeURIComponent(id)}`;

// No argument: personal bookings + every group booking the user can see. Or filter by one trip / one group.
export function listBookings({ tripId, groupId } = {}) {
  const params = new URLSearchParams();
  if (tripId) params.set("trip_id", tripId);
  if (groupId) params.set("group_id", groupId);
  const query = params.toString();
  return apiRequest(`/api/bookings${query ? `?${query}` : ""}`, { fallbackMessage: "Your bookings could not be loaded." });
}
export const createBooking = (payload) => apiRequest("/api/bookings", { method: "POST", body: payload });
export const updateBooking = (id, payload) => apiRequest(b(id), { method: "PUT", body: payload });
export const deleteBooking = (id) => apiRequest(b(id), { method: "DELETE" });
export const shareBookingToChat = (id) => apiRequest(`${b(id)}/share`, { method: "POST" });

export function uploadBookingFile(id, file) {
  const body = new FormData();
  body.append("file", file);
  return apiRequest(`${b(id)}/files`, { method: "POST", body });
}
export const deleteBookingFile = (id, fileId) => apiRequest(`${b(id)}/files/${encodeURIComponent(fileId)}`, { method: "DELETE" });
// Files are private: this URL only works for a logged-in user who may see the booking (the cookie is sent with the request).
export const bookingFileUrl = (id, fileId, download = false) => `${import.meta.env.VITE_API_BASE_URL || ""}${b(id)}/files/${encodeURIComponent(fileId)}${download ? "?download=1" : ""}`;
export const ACCEPTED_FILE_TYPES = "application/pdf,image/png,image/jpeg,image/webp";
export const MAX_FILE_MB = 5;
export const MAX_FILES_PER_BOOKING = 5;
