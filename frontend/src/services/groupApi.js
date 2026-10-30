import { apiRequest } from "./apiClient";

const g = (id) => `/api/groups/${encodeURIComponent(id)}`;

export const listGroups = () => apiRequest("/api/groups", { fallbackMessage: "Your groups could not be loaded." });
export const createGroup = (name, description) => apiRequest("/api/groups", { method: "POST", body: { name, description } });
export const joinGroup = (inviteCode) => apiRequest("/api/groups/join", { method: "POST", body: { invite_code: inviteCode } });
export const getGroup = (id) => apiRequest(g(id), { fallbackMessage: "This group could not be loaded." });
export const deleteGroup = (id) => apiRequest(g(id), { method: "DELETE" });
export const leaveGroup = (id) => apiRequest(`${g(id)}/members/me`, { method: "DELETE" });

export const listMessages = (id, after, signal) =>
  apiRequest(`${g(id)}/messages${after ? `?after=${encodeURIComponent(after)}` : ""}`, { signal });
export const sendMessage = (id, text) => apiRequest(`${g(id)}/messages`, { method: "POST", body: { text } });

export const listSuggestions = (id) => apiRequest(`${g(id)}/suggestions`, { fallbackMessage: "Suggestions could not be loaded." });
export const addSuggestion = (id, payload) => apiRequest(`${g(id)}/suggestions`, { method: "POST", body: payload });
export const deleteSuggestion = (id, sid) => apiRequest(`${g(id)}/suggestions/${encodeURIComponent(sid)}`, { method: "DELETE" });
export const vote = (id, sid) => apiRequest(`${g(id)}/suggestions/${encodeURIComponent(sid)}/vote`, { method: "PUT" });
export const removeVote = (id, sid) => apiRequest(`${g(id)}/suggestions/${encodeURIComponent(sid)}/vote`, { method: "DELETE" });
export const decide = (id, suggestionId) => apiRequest(`${g(id)}/decide`, { method: "POST", body: { suggestion_id: suggestionId } });
export const reopenVoting = (id) => apiRequest(`${g(id)}/decision`, { method: "DELETE" });
