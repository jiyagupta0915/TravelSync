const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Packing list request could not be completed.");
  return data;
}

export function getPackingList(tripId) {
  return request(`/api/trips/${tripId}/packing-list`);
}

export function generatePackingList(tripId, { activities = [], regenerate = false } = {}) {
  return request(`/api/trips/${tripId}/packing-list`, {
    method: "POST",
    body: JSON.stringify({ activities, regenerate }),
  });
}

export function updatePackingList(tripId, items) {
  return request(`/api/trips/${tripId}/packing-list`, {
    method: "PATCH",
    body: JSON.stringify({ items }),
  });
}

export function setTripDates(tripId, startDate, endDate) {
  return request(`/api/trips/${tripId}/packing-list/dates`, {
    method: "PUT",
    body: JSON.stringify({ start_date: startDate, end_date: endDate }),
  });
}