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
  if (!response.ok) throw new Error(data.error || "Trip request could not be completed.");
  return data;
}

export function getTrips() {
  return request("/api/trips");
}

export function createTrip(payload) {
  return request("/api/trips", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
