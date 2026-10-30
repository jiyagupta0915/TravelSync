import { apiRequest } from "./apiClient";

export async function updateProfile(changes) {
  const data = await apiRequest("/api/users/me", { method: "PATCH", body: changes });
  return data.user;
}

export async function saveSettings(settings) {
  const data = await apiRequest("/api/users/me/settings", { method: "PUT", body: settings });
  return data.settings;
}
