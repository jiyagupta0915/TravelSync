import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChatWidget from "./ChatWidget";
import { renderWithProviders } from "../../test/helpers";
import { ApiError } from "../../services/apiClient";

vi.mock("../../services/chatApi", () => ({ askAssistant: vi.fn() }));
import { askAssistant } from "../../services/chatApi";

const reply = (text, extra = {}) => ({ reply: { text, items: [], links: [], suggestions: [], ...extra }, destination: null });

function setup() {
  render(renderWithProviders(<ChatWidget />));
  return userEvent.setup();
}

beforeEach(() => vi.clearAllMocks());

describe("TravelSync assistant widget", () => {
  it("is closed until the floating button is used, then greets with starter questions", async () => {
    const user = setup();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open TravelSync assistant" }));
    const panel = screen.getByRole("dialog", { name: "TravelSync assistant" });
    expect(within(panel).getByText(/I'm the TravelSync assistant/)).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: "Top places in Goa" })).toBeInTheDocument();
    expect(within(panel).getByLabelText("Your question")).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("sends a typed question, shows the answer with its list and link, and carries the destination into the next question", async () => {
    askAssistant.mockResolvedValueOnce({ ...reply("Top places to visit in Goa:", {
      items: ["1. Baga Beach"], links: [{ label: "My Trips", to: "/trips" }], suggestions: ["Tell me about Goa"] }), destination: "Goa" });
    askAssistant.mockResolvedValueOnce(reply("Goa is in Goa (West India)."));
    const user = setup();
    await user.click(screen.getByRole("button", { name: "Open TravelSync assistant" }));
    await user.type(screen.getByLabelText("Your question"), "top places in goa{Enter}");

    expect(askAssistant).toHaveBeenCalledWith("top places in goa", null);
    const log = screen.getByRole("log");
    expect(within(log).getByText("top places in goa")).toBeInTheDocument();                 // my question
    expect(await within(log).findByText("Top places to visit in Goa:")).toBeInTheDocument();
    expect(within(log).getByText("1. Baga Beach")).toBeInTheDocument();
    expect(within(log).getByRole("link", { name: "My Trips" })).toHaveAttribute("href", "/trips");
    expect(screen.getByLabelText("Your question")).toHaveValue("");
    expect(within(log).queryByRole("button", { name: "Top places in Goa" })).not.toBeInTheDocument();   // starters replaced by follow-ups

    await user.click(within(log).getByRole("button", { name: "Tell me about Goa" }));        // a follow-up chip
    expect(askAssistant).toHaveBeenLastCalledWith("Tell me about Goa", "Goa");
    expect(await within(log).findByText("Goa is in Goa (West India).")).toBeInTheDocument();
  });

  it("shows a failure as a message in the conversation and lets the user try again", async () => {
    askAssistant.mockRejectedValueOnce(new ApiError("The assistant couldn't answer that right now.", { status: 500 }));
    askAssistant.mockResolvedValueOnce(reply("Hi Asha!"));
    const user = setup();
    await user.click(screen.getByRole("button", { name: "Open TravelSync assistant" }));
    await user.type(screen.getByLabelText("Your question"), "hello{Enter}");
    expect(await screen.findByText("The assistant couldn't answer that right now.")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Your question"), "hello{Enter}");
    expect(await screen.findByText("Hi Asha!")).toBeInTheDocument();
  });

  it("labels an answer that came from the AI model, and only that one", async () => {
    askAssistant.mockResolvedValueOnce({ ...reply("October to March is pleasant."), source: "ai-model" });
    askAssistant.mockResolvedValueOnce({ ...reply("Goa is in Goa (West India)."), source: "travelsync-data" });
    const user = setup();
    await user.click(screen.getByRole("button", { name: "Open TravelSync assistant" }));
    await user.type(screen.getByLabelText("Your question"), "best season?{Enter}");
    const generated = (await screen.findByText("October to March is pleasant.")).closest("li");
    expect(within(generated).getByText(/AI-generated answer/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Your question"), "goa{Enter}");
    const builtIn = (await screen.findByText("Goa is in Goa (West India).")).closest("li");
    expect(within(builtIn).queryByText(/AI-generated/)).not.toBeInTheDocument();
  });

  it("does not send an empty question", async () => {
    const user = setup();
    await user.click(screen.getByRole("button", { name: "Open TravelSync assistant" }));
    expect(screen.getByRole("button", { name: "Send question" })).toBeDisabled();
    await user.type(screen.getByLabelText("Your question"), "   {Enter}");
    expect(askAssistant).not.toHaveBeenCalled();
  });
});
