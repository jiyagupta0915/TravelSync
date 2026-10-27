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
  if (!response.ok) throw new Error(data.error || "Stays could not be loaded.");
  return data;
}

export function getTripStays(tripId) {
  return request(`/api/trips/${tripId}/stays`);
}


export function getSavedStays(tripId) {
  return request(`/api/trips/${tripId}/stays/saved`);
}

export function saveStay(tripId, stayKey) {
  return request(`/api/trips/${tripId}/stays/saved`, {
    method: "POST",
    body: JSON.stringify({ stay_key: stayKey }),
  });
}

export function removeSavedStay(tripId, stayKey) {
  return request(`/api/trips/${tripId}/stays/saved/${encodeURIComponent(stayKey)}`, { method: "DELETE" });
}