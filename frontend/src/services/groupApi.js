import { apiRequest } from "./apiClient";

const g = (id) => `/api/groups/${encodeURIComponent(id)}`;

export const listGroups = () => apiRequest("/api/groups", { fallbackMessage: "Your groups could not be loaded." });
export const createGroup = (name, description) => apiRequest("/api/groups", { method: "POST", body: { name, description } });
export const joinGroup = (inviteCode) => apiRequest("/api/groups/join", { method: "POST", body: { invite_code: inviteCode } });
export const getGroup = (id) => apiRequest(g(id), { fallbackMessage: "This group could not be loaded." });
export const deleteGroup = (id) => apiRequest(g(id), { method: "DELETE" });
export const leaveGroup = (id) => apiRequest(`${g(id)}/members/me`, { method: "DELETE" });

// Soft delete: the message stays in the history as "This message was deleted". Only its author can do this.
export const deleteMessage = (id, messageId) => apiRequest(`${g(id)}/messages/${encodeURIComponent(messageId)}`, { method: "DELETE" });

// `after` = only newer than this timestamp (polling). `before` = a message id: the page of older messages.
export function listMessages(id, after, signal, before) {
  const params = new URLSearchParams();
  if (after) params.set("after", after);
  if (before) params.set("before", before);
  const query = params.toString();
  return apiRequest(`${g(id)}/messages${query ? `?${query}` : ""}`, { signal });
}
// Live chat socket (receive-only; messages are still sent with sendMessage). Works through the Vite proxy in dev.
export function chatSocketUrl(id) {
  const base = import.meta.env.VITE_API_BASE_URL || window.location.origin;
  return `${base.replace(/^http/, "ws")}${g(id)}/ws`;
}
// Unread chat messages: { total, groups: { [groupId]: count } } across the user's groups, and "I've seen this chat".
export const getUnreadChats = (signal) => apiRequest("/api/groups/unread", { signal });
export const markChatRead = (id) => apiRequest(`${g(id)}/read`, { method: "POST" });
// Read receipts: [{ id, name, seen_id }] for the other members. A message with id <= seen_id was seen by that member.
export const listReads = (id, signal) => apiRequest(`${g(id)}/reads`, { signal });
export const sendMessage = (id, text) => apiRequest(`${g(id)}/messages`, { method: "POST", body: { text } });

export const listSuggestions = (id) => apiRequest(`${g(id)}/suggestions`, { fallbackMessage: "Suggestions could not be loaded." });
export const addSuggestion = (id, payload) => apiRequest(`${g(id)}/suggestions`, { method: "POST", body: payload });
export const deleteSuggestion = (id, sid) => apiRequest(`${g(id)}/suggestions/${encodeURIComponent(sid)}`, { method: "DELETE" });
export const vote = (id, sid) => apiRequest(`${g(id)}/suggestions/${encodeURIComponent(sid)}/vote`, { method: "PUT" });
export const removeVote = (id, sid) => apiRequest(`${g(id)}/suggestions/${encodeURIComponent(sid)}/vote`, { method: "DELETE" });
export const decide = (id, suggestionId) => apiRequest(`${g(id)}/decide`, { method: "POST", body: { suggestion_id: suggestionId } });
export const reopenVoting = (id) => apiRequest(`${g(id)}/decision`, { method: "DELETE" });
