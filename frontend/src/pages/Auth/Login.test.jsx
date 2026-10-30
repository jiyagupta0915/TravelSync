import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Login from "./Login";
import { renderWithProviders } from "../../test/helpers";

describe("Login", () => {
  it("lets existing users in with ANY password the server accepts (no new-password policy on login)", async () => {
    const login = vi.fn(async () => ({ id: "1" }));
    const user = userEvent.setup();
    render(renderWithProviders(<Login />, { auth: { status: "unauthenticated", user: null, isAuthenticated: false, login } }));
    await user.type(screen.getByLabelText("Email"), "old@example.com");
    await user.type(screen.getByLabelText("Password"), "weakpass");
    await user.click(screen.getByRole("button", { name: "Log In" }));
    expect(login).toHaveBeenCalledWith("old@example.com", "weakpass");
  });

  it("links to password recovery and shows server errors", async () => {
    const login = vi.fn(async () => { throw new Error("Invalid email or password."); });
    const user = userEvent.setup();
    render(renderWithProviders(<Login />, { auth: { status: "unauthenticated", user: null, isAuthenticated: false, login } }));
    expect(screen.getByRole("link", { name: /forgot password/i })).toHaveAttribute("href", "/forgot-password");
    await user.type(screen.getByLabelText("Email"), "a@b.co");
    await user.type(screen.getByLabelText("Password"), "x");
    await user.click(screen.getByRole("button", { name: "Log In" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
  });
});
