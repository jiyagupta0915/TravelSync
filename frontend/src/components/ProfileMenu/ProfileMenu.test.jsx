import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProfileMenu from "./ProfileMenu";
import { renderWithProviders } from "../../test/helpers";

function setup(auth) {
  return render(renderWithProviders(<><button>outside</button><ProfileMenu /></>, { auth }));
}

describe("ProfileMenu", () => {
  it("is closed initially and exposes menu semantics", () => {
    setup();
    const button = screen.getByRole("button", { name: /account menu for asha rao/i });
    expect(button).toHaveAttribute("aria-haspopup", "menu");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(button).toHaveTextContent("AR");
  });

  it("opens on click and shows name, email, avatar initials and the three actions", async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole("button", { name: /account menu/i }));
    const menu = screen.getByRole("menu");
    expect(menu).toHaveTextContent("Asha Rao");
    expect(menu).toHaveTextContent("asha@example.com");
    expect(screen.getByRole("menuitem", { name: /profile/i })).toHaveAttribute("href", "/profile");
    expect(screen.getByRole("menuitem", { name: /settings/i })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("menuitem", { name: /log out/i })).toBeInTheDocument();
    expect(menu).not.toHaveTextContent(/undefined|null/);
  });

  it("supports keyboard: ArrowDown opens + focuses first item, arrows/Home/End move, Escape closes and restores focus", async () => {
    const user = userEvent.setup();
    setup();
    const button = screen.getByRole("button", { name: /account menu/i });
    button.focus();
    await user.keyboard("{ArrowDown}");
    const [profile, settings, logout] = screen.getAllByRole("menuitem");
    expect(profile).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(settings).toHaveFocus();
    await user.keyboard("{End}");
    expect(logout).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(profile).toHaveFocus();            // wraps
    await user.keyboard("{Home}");
    expect(profile).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(button).toHaveFocus();
  });

  it("closes on outside click", async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole("button", { name: /account menu/i }));
    await user.click(screen.getByRole("button", { name: "outside" }));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("logs out through the auth context", async () => {
    const user = userEvent.setup();
    const logout = vi.fn(async () => true);
    setup({ logout });
    await user.click(screen.getByRole("button", { name: /account menu/i }));
    await user.click(screen.getByRole("menuitem", { name: /log out/i }));
    expect(logout).toHaveBeenCalledTimes(1);
  });

  it("never shows 'undefined' when profile fields are missing", async () => {
    const user = userEvent.setup();
    setup({ user: { id: "x" } });
    const button = screen.getByRole("button", { name: /account menu/i });
    expect(button).not.toHaveTextContent(/undefined|null/);
    await user.click(button);
    expect(screen.getByRole("menu")).not.toHaveTextContent(/undefined|null/);
  });
});
