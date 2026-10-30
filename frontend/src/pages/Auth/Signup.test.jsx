import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Signup from "./Signup";
import { renderWithProviders } from "../../test/helpers";
import { ApiError } from "../../services/apiClient";

const unauth = { status: "unauthenticated", user: null, isAuthenticated: false };

function setup(extra = {}) {
  const signup = vi.fn(async () => ({ id: "1" }));
  render(renderWithProviders(<Signup />, { auth: { ...unauth, signup, ...extra } }));
  return { signup, user: userEvent.setup() };
}

const rule = (name) => screen.getByText(name).closest("li");

describe("Signup", () => {
  it("shows the password requirements up front and updates them live", async () => {
    const { user } = setup();
    expect(screen.getByText(/your password needs/i)).toBeInTheDocument();
    expect(rule("At least 8 characters")).not.toHaveClass("is-met");
    await user.type(screen.getByLabelText("Password"), "abcdefgh");
    expect(rule("At least 8 characters")).toHaveClass("is-met");
    expect(rule("One lowercase letter (a–z)")).toHaveClass("is-met");
    expect(rule("One uppercase letter (A–Z)")).not.toHaveClass("is-met");
    expect(within(rule("One uppercase letter (A–Z)")).getByText(/not met yet/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Password"), "A1!");
    for (const li of screen.getAllByRole("listitem")) expect(li).toHaveClass("is-met");
  });

  it("shows a mismatch message as soon as the confirmation differs", async () => {
    const { user } = setup();
    await user.type(screen.getByLabelText("Password"), "Str0ng!Passw0rd");
    await user.type(screen.getByLabelText("Confirm Password"), "Str0ng!");
    expect(screen.getByRole("alert")).toHaveTextContent("Passwords do not match.");
  });

  it("blocks submission of invalid forms, focuses the first bad field, and does not call the API", async () => {
    const { user, signup } = setup();
    await user.type(screen.getByLabelText("Full Name"), "Asha Rao");
    await user.type(screen.getByLabelText("Email"), "asha@example.com");
    await user.type(screen.getByLabelText("Password"), "weak");
    await user.type(screen.getByLabelText("Confirm Password"), "weak");
    await user.click(screen.getByRole("button", { name: "Create Account" }));
    expect(signup).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Password")).toHaveFocus();
    expect(screen.getByText(/doesn't meet all the requirements/i)).toBeInTheDocument();
  });

  it("submits trimmed values when everything is valid", async () => {
    const { user, signup } = setup();
    await user.type(screen.getByLabelText("Full Name"), "  Asha Rao ");
    await user.type(screen.getByLabelText("Email"), "asha@example.com");
    await user.type(screen.getByLabelText("Password"), "Str0ng!Passw0rd");
    await user.type(screen.getByLabelText("Confirm Password"), "Str0ng!Passw0rd");
    await user.click(screen.getByRole("button", { name: "Create Account" }));
    expect(signup).toHaveBeenCalledWith("Asha Rao", "asha@example.com", "Str0ng!Passw0rd");
  });

  it("keeps the show/hide password toggle working", async () => {
    const { user } = setup();
    const field = screen.getByLabelText("Password");
    expect(field).toHaveAttribute("type", "password");
    await user.click(screen.getAllByRole("button", { name: "Show password" })[0]);
    expect(field).toHaveAttribute("type", "text");
  });

  it("shows the server's explanation next to the email field on duplicates", async () => {
    const err = new ApiError("An account with this email already exists. Please log in.", { status: 409, kind: "validation" });
    const { user } = setup({ signup: vi.fn(async () => { throw err; }) });
    await user.type(screen.getByLabelText("Full Name"), "Asha Rao");
    await user.type(screen.getByLabelText("Email"), "asha@example.com");
    await user.type(screen.getByLabelText("Password"), "Str0ng!Passw0rd");
    await user.type(screen.getByLabelText("Confirm Password"), "Str0ng!Passw0rd");
    await user.click(screen.getByRole("button", { name: "Create Account" }));
    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
  });
});
