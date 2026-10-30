import { apiRequest } from "./apiClient";

// Login / signup 401s are "wrong credentials", not an expired session, so they skip the global handler.
export async function login(email, password) {
  const data = await apiRequest("/api/auth/login", { method: "POST", body: { email, password }, skipUnauthorizedHandler: true, fallbackMessage: "Could not log in." });
  return data.user;
}

export async function signup(name, email, password) {
  const data = await apiRequest("/api/auth/signup", { method: "POST", body: { name, email, password }, skipUnauthorizedHandler: true, fallbackMessage: "Could not create your account." });
  return data.user;
}

export async function logout() {
  await apiRequest("/api/auth/logout", { method: "POST", skipUnauthorizedHandler: true });
}

// Resolves to the user, or null when there is no valid session. Throws ApiError (network / 5xx) when the
// server could not be asked - callers must NOT treat that as "logged out".
export async function getCurrentUser() {
  const data = await apiRequest("/api/auth/me", { skipUnauthorizedHandler: true });
  return data.user ?? null;
}

export function changePassword(currentPassword, newPassword) {
  return apiRequest("/api/auth/change-password", { method: "POST", body: { current_password: currentPassword, new_password: newPassword }, skipUnauthorizedHandler: true });
}

export function getRecoveryStatus() {
  return apiRequest("/api/auth/recovery-status", { skipUnauthorizedHandler: true });
}

export function forgotPassword(email) {
  return apiRequest("/api/auth/forgot-password", { method: "POST", body: { email }, skipUnauthorizedHandler: true });
}

export function resetPassword(token, newPassword) {
  return apiRequest("/api/auth/reset-password", { method: "POST", body: { token, new_password: newPassword }, skipUnauthorizedHandler: true });
}
