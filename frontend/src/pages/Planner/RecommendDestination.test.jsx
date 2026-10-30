import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RecommendDestination from "./RecommendDestination";
import { renderWithProviders, setViewport } from "../../test/helpers";
import { ApiError } from "../../services/apiClient";

vi.mock("../../services/recommendationApi", () => ({
  getFeatures: vi.fn(async () => ({ interest_features: ["Mountain", "Beach", "Nature"] })),
  searchStartingLocations: vi.fn(async () => ({ results: [{ Location: "Delhi", State: "Delhi", Latitude: 28.6, Longitude: 77.2 }] })),
  recommendDestinations: vi.fn(),
  searchDestinations: vi.fn(async () => ({ results: [] })),
}));
vi.mock("../../services/tripApi", () => ({ createTrip: vi.fn() }));
vi.mock("../../services/placesApi", () => ({ getTopPlaces: vi.fn(async () => ({ places: [] })) }));

import { recommendDestinations } from "../../services/recommendationApi";

const result = (name, score) => ({
  Destination: name, State: "Goa", Region: "West", final_score: score, distance_km: 900, estimated_trip_budget_inr: 18000,
  best_for: [], explanation: [], matched_features: [], missing_features: [],
});

async function fillValidForm(user) {
  await user.type(screen.getByPlaceholderText("Search a city or state"), "Del");
  await user.click(await screen.findByRole("button", { name: /Delhi/ }));
}

function setup() {
  setViewport(1280);
  Element.prototype.scrollIntoView = vi.fn();
  render(renderWithProviders(<RecommendDestination />));
  return userEvent.setup();
}

const submit = () => screen.getByRole("button", { name: /find my destinations|finding matches/i });

beforeEach(() => vi.clearAllMocks());

describe("Find Destination feedback", () => {
  it("shows loading, blocks duplicate submits, announces the count and scrolls to results (no timers)", async () => {
    let resolve;
    recommendDestinations.mockReturnValue(new Promise((r) => { resolve = r; }));
    const user = setup();
    await fillValidForm(user);

    await user.click(submit());
    await user.click(submit());                                        // second click while loading
    expect(recommendDestinations).toHaveBeenCalledTimes(1);
    expect(submit()).toBeDisabled();
    expect(submit()).toHaveAttribute("aria-busy", "true");

    resolve({ recommendations: [result("Goa", 0.9), result("Manali", 0.8)], rules: null });
    expect(await screen.findByText(/found 2 destinations for your trip/i)).toBeInTheDocument();
    await waitFor(() => expect(Element.prototype.scrollIntoView).toHaveBeenCalledTimes(1));
    expect(screen.getAllByText(/Found 2 matching destinations\./)[0]).toBeInTheDocument();   // screen-reader announcement
  });

  it("sends numeric payloads in the existing units and preserves the ranking order", async () => {
    recommendDestinations.mockResolvedValue({ recommendations: [result("Goa", 0.9), result("Manali", 0.8)], rules: null });
    const user = setup();
    await fillValidForm(user);
    await user.click(submit());
    const [payload] = recommendDestinations.mock.calls[0];
    expect(payload).toMatchObject({ duration: 5, budget: 20000, max_distance_km: 2000, start_lat: 28.6, start_lon: 77.2, top_n: 6 });
    expect(typeof payload.budget).toBe("number");
    await screen.findByText(/found 2 destinations/i);
    const names = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(names.indexOf("Goa")).toBeLessThan(names.indexOf("Manali"));
  });

  it("shows an empty-result state (not an error) and does not scroll", async () => {
    recommendDestinations.mockResolvedValue({ recommendations: [], rules: null });
    const user = setup();
    await fillValidForm(user);
    await user.click(submit());
    await waitFor(() => expect(recommendDestinations).toHaveBeenCalled());
    expect(await screen.findAllByText(/no destinations matched/i)).not.toHaveLength(0);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
  });

  it.each([
    ["network", new ApiError("Can't reach TravelSync. Check your internet connection and try again.", { kind: "network" }), /can't reach travelsync/i],
    ["server", new ApiError("The server ran into a problem. Please try again in a moment.", { status: 500, kind: "server" }), /server ran into a problem/i],
    ["validation", new ApiError("budget: Input should be greater than 0", { status: 422, kind: "validation" }), /budget: input should be greater/i],
  ])("shows a visible %s error and re-enables the button", async (_n, error, pattern) => {
    recommendDestinations.mockRejectedValue(error);
    const user = setup();
    await fillValidForm(user);
    await user.click(submit());
    expect(await screen.findByRole("alert")).toHaveTextContent(pattern);
    expect(submit()).toBeEnabled();
  });

  it("validates before calling the API and focuses the first invalid field", async () => {
    const user = setup();
    await user.click(submit());                              // no starting location chosen
    expect(recommendDestinations).not.toHaveBeenCalled();
    expect(screen.getByPlaceholderText("Search a city or state")).toHaveFocus();
    expect(screen.getByText(/select your starting location/i)).toBeInTheDocument();
  });

  it("rejects empty, zero and excessive budget/distance without turning empty into 0", async () => {
    const user = setup();
    await fillValidForm(user);
    const budget = screen.getByLabelText("Total budget in rupees");
    await user.clear(budget);
    expect(budget).toHaveValue("");                          // stays empty while typing
    await user.click(submit());
    expect(screen.getByText(/enter your budget/i)).toBeInTheDocument();
    expect(budget).toHaveFocus();
    await user.type(budget, "0");
    await user.click(submit());
    expect(screen.getByText(/budget must be at least 1/i)).toBeInTheDocument();
    await user.clear(budget); await user.type(budget, "99999999");
    await user.click(submit());
    expect(screen.getByText(/can't be more than/i)).toBeInTheDocument();
    const distance = screen.getByLabelText("Maximum travel distance in kilometres");
    await user.clear(distance); await user.type(distance, "10001");
    await user.click(submit());
    expect(recommendDestinations).not.toHaveBeenCalled();
  });

  it("lets a late response from an older request NOT overwrite the newer one", async () => {
    const resolvers = [];
    recommendDestinations.mockImplementation((_p, signal) => new Promise((resolve, reject) => {
      resolvers.push(resolve);
      signal.addEventListener("abort", () => reject(Object.assign(new Error("aborted"), { name: "AbortError" })));
    }));
    const user = setup();
    await fillValidForm(user);
    await user.click(submit());
    // reset (aborts the first request), then search again
    await user.click(screen.getByRole("button", { name: /reset/i }));
    await fillValidForm(user);
    await user.click(submit());
    expect(recommendDestinations).toHaveBeenCalledTimes(2);
    resolvers[0]({ recommendations: [result("OLD-RESULT", 0.1)], rules: null });     // stale answer arrives late
    resolvers[1]({ recommendations: [result("NEW-RESULT", 0.9)], rules: null });
    expect(await screen.findAllByText("NEW-RESULT")).not.toHaveLength(0);
    expect(screen.queryByText("OLD-RESULT")).not.toBeInTheDocument();
  });
});
