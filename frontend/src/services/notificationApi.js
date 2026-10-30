import { apiRequest } from "./apiClient";

export const listNotifications = (signal) => apiRequest("/api/notifications", { signal });
export const markAllRead = () => apiRequest("/api/notifications/read-all", { method: "POST" });
export const markRead = (id) => apiRequest(`/api/notifications/${encodeURIComponent(id)}/read`, { method: "POST" });
