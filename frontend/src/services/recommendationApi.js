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
  if (!response.ok) throw new Error(data.error || "The request could not be completed.");
  return data;
}

export function getFeatures() {
  return request("/api/features");
}

export function searchStartingLocations(query = "") {
  const params = new URLSearchParams({ q: query.trim(), limit: "15" });
  return request(`/api/start-locations/search?${params.toString()}`);
}

export function searchDestinations(query = "") {
  const params = new URLSearchParams({ q: query.trim(), limit: "12" });
  return request(`/api/destinations/search?${params.toString()}`);
}

export function recommendDestinations(payload) {
  return request("/api/recommend", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getApiHealth() {
  return request("/api/health");
}
