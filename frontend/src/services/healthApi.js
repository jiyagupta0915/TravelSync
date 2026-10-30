import { apiRequest } from "./apiClient";

export function getTravelHealth(destination, month, signal) {
  const params = month ? `?month=${encodeURIComponent(month)}` : "";
  return apiRequest(`/api/travel-health/${encodeURIComponent(destination)}${params}`, { signal, fallbackMessage: "Could not load travel health information." });
}
