import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes, useLocation } from "react-router-dom";
import AppShell from "./AppShell";
import { renderWithProviders, setViewport } from "../../test/helpers";

vi.mock("../../services/notificationApi", () => ({
  listNotifications: vi.fn(async () => ({ notifications: [], unread_count: 0 })),
  markAllRead: vi.fn(), markRead: vi.fn(),
}));

function Where() {
  return <p data-testid="where">{useLocation().pathname}</p>;
}

function renderShell(width, route = "/home") {
  setViewport(width);
  return render(renderWithProviders(
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/home" element={<><h1>Home page</h1><Where /></>} />
        <Route path="/trips" element={<><h1>Trips page</h1><Where /></>} />
      </Route>
    </Routes>,
    { route },
  ));
}

describe("desktop sidebar", () => {
  it("is open by default with visible labels and a collapse toggle", () => {
    renderShell(1280);
    const sidebar = screen.getByRole("complementary", { name: "Main navigation" });
    expect(sidebar).not.toHaveClass("sidebar--rail");
    expect(within(sidebar).getByText("My Trips")).toBeVisible();
    expect(screen.getByRole("button", { name: "Collapse sidebar" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.queryByRole("button", { name: "Open menu" })).not.toBeInTheDocument();   // no hamburger on desktop
  });

  it("collapses to a rail (content area is told to expand) and expands again", async () => {
    const user = userEvent.setup();
    const { container } = renderShell(1280);
    await user.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(screen.getByRole("complementary", { name: "Main navigation" })).toHaveClass("sidebar--rail");
    expect(container.querySelector(".dashboard")).toHaveClass("dashboard--collapsed");
    // icon-only links keep an accessible name
    expect(screen.getByRole("link", { name: "My Trips" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Expand sidebar" }));
    expect(screen.getByRole("complementary", { name: "Main navigation" })).not.toHaveClass("sidebar--rail");
  });

  it("keeps its collapsed state when navigating between pages", async () => {
    const user = userEvent.setup();
    renderShell(1280);
    await user.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    await user.click(screen.getByRole("link", { name: "My Trips" }));
    expect(screen.getByTestId("where")).toHaveTextContent("/trips");
    expect(screen.getByRole("complementary", { name: "Main navigation" })).toHaveClass("sidebar--rail");
  });

  it("renders exactly one sidebar", () => {
    renderShell(1280);
    expect(screen.getAllByRole("complementary")).toHaveLength(1);
  });
});

describe("mobile drawer", () => {
  it("starts closed (inert, no dialog) with a hamburger", () => {
    const { container } = renderShell(390);
    const hamburger = screen.getByRole("button", { name: "Open menu" });
    expect(hamburger).toHaveAttribute("aria-expanded", "false");
    expect(container.querySelector("#app-sidebar")).toHaveAttribute("inert");
    expect(screen.queryByTestId("sidebar-backdrop")).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens with the hamburger, moving focus into the drawer", async () => {
    const user = userEvent.setup();
    renderShell(390);
    await user.click(screen.getByRole("button", { name: "Open menu" }));
    const drawer = screen.getByRole("dialog", { name: "Main navigation" });
    expect(drawer).toHaveAttribute("aria-modal", "true");
    expect(screen.getByTestId("sidebar-backdrop")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close menu" })).toHaveFocus();
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("closes with the close button and returns focus to the hamburger", async () => {
    const user = userEvent.setup();
    renderShell(390);
    await user.click(screen.getByRole("button", { name: "Open menu" }));
    await user.click(screen.getByRole("button", { name: "Close menu" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open menu" })).toHaveFocus();
    expect(document.body.style.overflow).not.toBe("hidden");
  });

  it("closes on backdrop click", async () => {
    const user = userEvent.setup();
    renderShell(390);
    await user.click(screen.getByRole("button", { name: "Open menu" }));
    await user.click(screen.getByTestId("sidebar-backdrop"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    const user = userEvent.setup();
    renderShell(390);
    await user.click(screen.getByRole("button", { name: "Open menu" }));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes after choosing a navigation link, and navigates", async () => {
    const user = userEvent.setup();
    renderShell(390);
    await user.click(screen.getByRole("button", { name: "Open menu" }));
    await user.click(screen.getByRole("link", { name: "My Trips" }));
    expect(screen.getByTestId("where")).toHaveTextContent("/trips");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByTestId("sidebar-backdrop")).not.toBeInTheDocument();
  });

  it("keeps Tab focus inside the open drawer", async () => {
    const user = userEvent.setup();
    renderShell(390);
    await user.click(screen.getByRole("button", { name: "Open menu" }));
    const drawer = screen.getByRole("dialog");
    for (let i = 0; i < 20; i += 1) {
      await user.tab();
      expect(drawer.contains(document.activeElement)).toBe(true);
    }
  });
});

describe("the sidebar's real destinations", () => {
  it("has no placeholder '#' links", () => {
    renderShell(1280);
    const sidebar = screen.getByRole("complementary", { name: "Main navigation" });
    for (const link of within(sidebar).getAllByRole("link")) expect(link.getAttribute("href")).not.toBe("#");
    expect(within(sidebar).getByRole("link", { name: "Groups" })).toHaveAttribute("href", "/groups");
    expect(within(sidebar).getByRole("link", { name: "Bookings" })).toHaveAttribute("href", "/bookings");
    expect(within(sidebar).getByRole("link", { name: "Profile" })).toHaveAttribute("href", "/profile");
    expect(within(sidebar).getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings");
  });
});
