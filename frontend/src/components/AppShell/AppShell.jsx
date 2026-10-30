import { useCallback, useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "../Sidebar/Sidebar";
import AppTopbar from "./AppTopbar";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import "./AppShell.css";

export const DESKTOP_QUERY = "(min-width: 901px)";

// Layout route for every signed-in page: ONE sidebar + ONE top bar + the page (<Outlet/>).
// It lives above the individual pages, so sidebar state is kept while navigating between them, and it is
// unmounted on logout, which discards that state (a new login starts again with the sidebar open).
//
//   desktop : sidebar open by default, `collapsed` toggles the icon rail, content width follows.
//   mobile  : sidebar is a drawer, closed by default. `drawerPath` remembers the page the drawer was opened on,
//             so navigating anywhere (link, back button) closes it without an effect.
export default function AppShell() {
  const isDesktop = useMediaQuery(DESKTOP_QUERY);
  const { pathname } = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerPath, setDrawerPath] = useState(null);

  const drawerOpen = !isDesktop && drawerPath === pathname;
  const hamburgerRef = useRef(null);
  const closeButtonRef = useRef(null);
  const sidebarRef = useRef(null);

  const openDrawer = useCallback(() => setDrawerPath(pathname), [pathname]);
  const dismissDrawer = useCallback(() => setDrawerPath(null), []);
  const closeDrawerAndRestoreFocus = useCallback(() => {
    setDrawerPath(null);
    hamburgerRef.current?.focus();
  }, []);

  // Drawer behaviours: Escape closes, Tab stays inside, background doesn't scroll, focus moves in.
  useEffect(() => {
    if (!drawerOpen) return undefined;
    closeButtonRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDrawerAndRestoreFocus();
        return;
      }
      if (event.key !== "Tab" || !sidebarRef.current) return;
      const focusable = sidebarRef.current.querySelectorAll("a[href], button:not([disabled])");
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [drawerOpen, closeDrawerAndRestoreFocus]);

  return (
    <div className={`dashboard${isDesktop && collapsed ? " dashboard--collapsed" : ""}`}>
      <a href="#main-content" className="skip-link">Skip to content</a>
      <Sidebar
        isDesktop={isDesktop}
        collapsed={collapsed}
        drawerOpen={drawerOpen}
        onToggleCollapse={() => setCollapsed((value) => !value)}
        onCloseDrawer={closeDrawerAndRestoreFocus}
        onNavigate={dismissDrawer}
        closeButtonRef={closeButtonRef}
        sidebarRef={sidebarRef}
      />
      {drawerOpen && <div className="sidebar-backdrop" onClick={closeDrawerAndRestoreFocus} aria-hidden="true" data-testid="sidebar-backdrop" />}

      <div className="dashboard__main">
        <AppTopbar showMenuButton={!isDesktop} menuOpen={drawerOpen} onOpenMenu={openDrawer} menuButtonRef={hamburgerRef} />
        <div id="main-content" tabIndex={-1} className="dashboard__page">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
