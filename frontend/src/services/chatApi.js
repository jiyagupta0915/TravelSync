import { apiRequest } from "./apiClient";

// Ask the TravelSync assistant. `destination` is what the conversation has been about so far (or null), so a
// follow-up like "what should I pack?" still makes sense. Returns { reply: { text, items, links, suggestions }, destination }.
export function askAssistant(message, destination) {
  return apiRequest("/api/chat", { method: "POST", body: { message, destination: destination || null }, fallbackMessage: "The assistant couldn't answer that right now." });
}
