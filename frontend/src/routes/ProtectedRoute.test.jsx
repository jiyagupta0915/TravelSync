import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import { renderWithProviders } from "../test/helpers";
import { ApiError } from "../services/apiClient";

function renderGuard(auth) {
  return render(renderWithProviders(
    <Routes>
      <Route path="/login" element={<h1>Login page</h1>} />
      <Route path="/secret" element={<ProtectedRoute><h1>Secret page</h1></ProtectedRoute>} />
    </Routes>,
    { route: "/secret", auth },
  ));
}

describe("ProtectedRoute", () => {
  it("shows the page when authenticated", () => {
    renderGuard({});
    expect(screen.getByRole("heading", { name: "Secret page" })).toBeInTheDocument();
  });
  it("shows a loading state, not the login page, while the session is being checked", () => {
    renderGuard({ status: "loading", user: null, isAuthenticated: false, isLoading: true });
    expect(screen.getByRole("status")).toHaveTextContent(/checking your session/i);
    expect(screen.queryByRole("heading", { name: "Login page" })).not.toBeInTheDocument();
  });
  it("redirects to login when the server says there is no session", () => {
    renderGuard({ status: "unauthenticated", user: null, isAuthenticated: false });
    expect(screen.getByRole("heading", { name: "Login page" })).toBeInTheDocument();
  });
  it("does NOT treat a service/network failure as logged out - offers Retry instead", async () => {
    const retry = vi.fn();
    const user = userEvent.setup();
    renderGuard({ status: "error", user: null, isAuthenticated: false, error: new ApiError("Can't reach TravelSync.", { kind: "network" }), retry });
    expect(screen.queryByRole("heading", { name: "Login page" })).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/can't reach travelsync/i);
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(retry).toHaveBeenCalled();
  });
});
