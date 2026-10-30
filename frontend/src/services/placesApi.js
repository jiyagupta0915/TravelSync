import { apiRequest } from "./apiClient";

export function getTopPlaces(destination, signal) {
  return apiRequest(`/api/places/${encodeURIComponent(destination)}`, { signal, fallbackMessage: "Top places could not be loaded." });
}
