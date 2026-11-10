import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import GroupDetail from "./GroupDetail";
import { renderWithProviders } from "../../test/helpers";

vi.mock("../../services/groupApi", () => ({
  getGroup: vi.fn(), listSuggestions: vi.fn(), listMessages: vi.fn(), chatSocketUrl: () => "ws://test/ws",
  addSuggestion: vi.fn(), decide: vi.fn(), deleteGroup: vi.fn(), deleteMessage: vi.fn(), deleteSuggestion: vi.fn(),
  leaveGroup: vi.fn(), listReads: vi.fn(), markChatRead: vi.fn(async () => ({ read: true })), removeVote: vi.fn(), reopenVoting: vi.fn(), sendMessage: vi.fn(), vote: vi.fn(),
}));
vi.mock("../../services/recommendationApi", () => ({
  getFeatures: vi.fn(async () => ({ interest_features: [] })), searchDestinations: vi.fn(async () => ({ results: [] })),
  getDestinationProfile: vi.fn(async () => ({ destination: {
    name: "Goa", state: "Goa", region: "West", ideal_days: 5, avg_daily_budget_inr: 3200, known_for: ["Beach", "Nightlife"], best_for: ["Friends"],
  } })),
}));
vi.mock("../../services/placesApi", () => ({
  getTopPlaces: vi.fn(async () => ({ places: [{ rank: 1, place_name: "Baga Beach", description: "Lively beach", category: "Beach", rating: 4.5, duration_hrs: 3, best_season: "Nov-Feb", popularity: 0.9 }] })),
}));
vi.mock("../../services/tripApi", () => ({ createTrip: vi.fn() }));

import { getGroup, listMessages, listReads, listSuggestions, markChatRead } from "../../services/groupApi";
import userEvent from "@testing-library/user-event";

// Stands in for the browser WebSocket so a test can push server events into the page.
class FakeSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static last = null;
  constructor() { this.readyState = FakeSocket.OPEN; FakeSocket.last = this; }
  send() {}
  close() {}
  push(data) { this.onmessage?.({ data: JSON.stringify(data) }); }
}

const GROUP = {
  id: "g1", name: "Goa gang", description: "", invite_code: "abc123", is_owner: true, member_count: 2, decided_suggestion_id: null,
  members: [{ id: "u1", name: "Asha Rao", is_owner: true, is_me: true }, { id: "u2", name: "Bob", is_owner: false, is_me: false }],
};
const suggestion = (votes) => ({
  id: "s1", destination: "Goa", state: "Goa", note: "", budget: 20000, duration: 5, preferences: ["Beach"], places: ["Baga Beach"],
  proposed_by: "Bob", proposed_by_me: false, votes, voted_by_me: false, is_decision: false, created_at: "2026-11-10T10:00:00+00:00",
});
const card = {
  id: "m1", kind: "suggestion", text: "Suggested Goa", author: "Bob", is_me: false, deleted: false, created_at: "2026-11-10T10:00:00+00:00",
  suggestion: { id: "s1", destination: "Goa", state: "Goa", note: "Beaches!", budget: 20000, duration: 5, preferences: ["Beach"], places: ["Baga Beach"] },
};

function setup() {
  render(renderWithProviders(<Routes><Route path="/groups/:groupId" element={<GroupDetail />} /></Routes>, { route: "/groups/g1" }));
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("WebSocket", FakeSocket);
  getGroup.mockResolvedValue({ group: GROUP });
  listSuggestions.mockResolvedValue({ suggestions: [] });
  listMessages.mockResolvedValue({ messages: [], has_more: false });
  listReads.mockResolvedValue({ reads: [] });
});

describe("Shared destinations in the group chat", () => {
  it("shows a pushed suggestion as a card with the criteria it was shared with", async () => {
    setup();
    const log = await screen.findByRole("log");
    await waitFor(() => expect(FakeSocket.last?.onmessage).toBeTypeOf("function"));
    act(() => FakeSocket.last.push({ type: "message", message: card }));

    expect(await within(log).findByText(/Bob suggested a destination/)).toBeInTheDocument();
    expect(within(log).getByText("5 days")).toBeInTheDocument();
    expect(within(log).getByText("₹20,000")).toBeInTheDocument();
    expect(within(log).getByText("Beach")).toBeInTheDocument();
    expect(within(log).getByText(/Baga Beach/)).toBeInTheDocument();
    expect(within(log).getByText(/Beaches!/)).toBeInTheDocument();
    expect(within(log).queryByRole("button", { name: /delete message/i })).not.toBeInTheDocument();
  });

  it("reloads suggestions and votes as soon as the socket says they changed", async () => {
    setup();
    await screen.findByText(/no suggestions yet/i);
    await waitFor(() => expect(FakeSocket.last?.onmessage).toBeTypeOf("function"));
    listSuggestions.mockResolvedValue({ suggestions: [suggestion(2)] });
    act(() => FakeSocket.last.push({ type: "suggestions_changed" }));
    expect(await screen.findByRole("button", { name: /Vote for Goa\. 2 votes/ })).toBeInTheDocument();
  });

  it("shows a removed suggestion's card as removed", async () => {
    listMessages.mockResolvedValue({ messages: [{ ...card, text: "", deleted: true, suggestion: undefined }], has_more: false });
    setup();
    expect(await screen.findByText("This suggestion was removed")).toBeInTheDocument();
  });
});

describe("Destination details from the ideas list", () => {
  it("opens the destination's overview, what was shared and its top places, then closes", async () => {
    listSuggestions.mockResolvedValue({ suggestions: [{ ...suggestion(2), note: "Beaches!" }] });
    setup();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "View details for Goa" }));

    const dialog = await screen.findByRole("dialog", { name: "About Goa" });
    expect(await within(dialog).findByText("Goa · West India")).toBeInTheDocument();
    expect(within(dialog).getByText("₹3,200")).toBeInTheDocument();
    expect(within(dialog).getByText("Nightlife")).toBeInTheDocument();
    expect(within(dialog).getByText("Friends")).toBeInTheDocument();
    expect(within(dialog).getByText(/Suggested by Bob · 2 votes/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Beaches!/)).toBeInTheDocument();
    expect(await within(dialog).findByRole("heading", { name: "Baga Beach" })).toBeInTheDocument();

    await user.click(within(dialog).getAllByRole("button", { name: "Close" })[1]);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("Marking the chat as read", () => {
  it("tells the server once per newest message while the chat is open, and not when it is empty", async () => {
    setup();
    await screen.findByText(/no messages yet/i);
    expect(markChatRead).not.toHaveBeenCalled();

    await waitFor(() => expect(FakeSocket.last?.onmessage).toBeTypeOf("function"));
    const heard = vi.fn();
    window.addEventListener("travelsync:chats-read", heard);
    act(() => FakeSocket.last.push({ type: "message", message: { id: "m2", kind: "text", text: "hello", author: "Bob", is_me: false, deleted: false, created_at: "2026-11-10T10:05:00+00:00" } }));
    await waitFor(() => expect(markChatRead).toHaveBeenCalledWith("g1"));
    await waitFor(() => expect(heard).toHaveBeenCalledTimes(1));          // the sidebar badge is told to refresh
    act(() => FakeSocket.last.push({ type: "message_deleted", id: "m2" }));   // same newest message: no second call
    expect(markChatRead).toHaveBeenCalledTimes(1);
    window.removeEventListener("travelsync:chats-read", heard);
  });
});

describe("Read receipts on my own messages", () => {
  // ids are 24-character hex, like the real ones: older messages sort first
  const mine = (id, text) => ({ id, kind: "text", text, author: "Asha Rao", is_me: true, deleted: false, created_at: `2026-11-10T10:0${id.at(-1)}:00+00:00` });
  const M1 = "0000000000000000000000a1", M2 = "0000000000000000000000a2";

  it("shows who has seen each message and updates live when another member opens the chat", async () => {
    listMessages.mockResolvedValue({ messages: [mine(M1, "first"), mine(M2, "second"), { ...mine("0000000000000000000000a3", "theirs"), is_me: false, author: "Bob" }], has_more: false });
    listReads.mockResolvedValue({ reads: [{ id: "u2", name: "Bob", seen_id: M1 }, { id: "u3", name: "Carol", seen_id: null }] });
    setup();
    const user = userEvent.setup();
    const first = (await screen.findByText("first")).closest("li");
    const second = screen.getByText("second").closest("li");
    expect(await within(first).findByRole("button", { name: "Seen by Bob" })).toBeInTheDocument();
    expect(within(second).getByRole("button", { name: "Not seen yet" })).toBeInTheDocument();
    expect(within(screen.getByText("theirs").closest("li")).queryByText(/seen/i)).not.toBeInTheDocument();   // only on my messages

    await user.click(within(first).getByRole("button", { name: "Seen by Bob" }));        // who exactly?
    expect(within(first).getByText("Seen: Bob")).toBeInTheDocument();
    expect(within(first).getByText("Not yet: Carol")).toBeInTheDocument();

    await waitFor(() => expect(FakeSocket.last?.onmessage).toBeTypeOf("function"));
    act(() => FakeSocket.last.push({ type: "read", user_id: "u3", seen_id: "0000000000000000000000a3" }));
    expect(await within(first).findByRole("button", { name: "Seen by everyone" })).toBeInTheDocument();
    expect(within(first).getByText("Seen: Bob, Carol")).toBeInTheDocument();
    expect(within(second).getByRole("button", { name: "Seen by Carol" })).toBeInTheDocument();
    act(() => FakeSocket.last.push({ type: "read", user_id: "u2", seen_id: "0000000000000000000000a3" }));
    expect(await within(second).findByRole("button", { name: "Seen by everyone" })).toBeInTheDocument();
  });

  it("shows plain text with one other member and nothing when alone in the group", async () => {
    listMessages.mockResolvedValue({ messages: [mine(M1, "first")], has_more: false });
    listReads.mockResolvedValue({ reads: [{ id: "u2", name: "Bob", seen_id: M1 }] });
    setup();
    const first = (await screen.findByText("first")).closest("li");
    expect(await within(first).findByText("Seen by Bob")).toBeInTheDocument();
    expect(within(first).queryByRole("button", { name: /seen/i })).not.toBeInTheDocument();
  });
});
