const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

// Permanently deletes a trip together with its packing list and saved stays.
export async function deleteTrip(tripId) {
  const response = await fetch(`${API_BASE_URL}/api/trips/${tripId}`, {
    method: "DELETE",
    credentials: "include",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || "The trip could not be deleted.");
    error.status = response.status;
    throw error;
  }
  return data;
}