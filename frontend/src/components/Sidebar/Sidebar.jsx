import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { Home, Compass, Briefcase, Users, Ticket, Backpack, BedDouble, HeartPulse, User, Settings, LogOut, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { useAuth } from "../../context/useAuth";
import "./Sidebar.css";

// The single sidebar for the whole logged-in area. It is rendered once, by AppShell, so its open/collapsed
// state survives navigation between pages. Behaviour:
//   desktop (wide)  : always visible; the toggle collapses it to an icon rail and the content expands.
//   mobile (narrow) : an off-canvas drawer, closed by default, opened from the top-bar hamburger.
const NAV_ITEMS = [
  { label: "Home", icon: Home, to: "/home" },
  { label: "Explore", icon: Compass, to: "/planner/recommend" },
  { label: "My Trips", icon: Briefcase, to: "/trips", also: ["/trip/"] },
  { label: "Packing", icon: Backpack, to: "/packing" },
  { label: "Health", icon: HeartPulse, to: "/health" },
  { label: "Groups", icon: Users, to: "/groups" },
  { label: "Stays", icon: BedDouble, to: "/stays" },
  { label: "Bookings", icon: Ticket, to: "/bookings" },
];

export default function Sidebar({ isDesktop, collapsed, drawerOpen, onToggleCollapse, onCloseDrawer, onNavigate, closeButtonRef, sidebarRef }) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const rail = isDesktop && collapsed;

  async function handleLogout() {
    onNavigate?.();
    await logout();                       // clears the session and every piece of signed-in UI state
    navigate("/login", { replace: true });
  }

  const linkClass = (item) => ({ isActive }) => {
    const active = isActive || (item.also || []).some((prefix) => pathname.startsWith(prefix));
    return `sidebar__nav-item${active ? " is-active" : ""}`;
  };

  const modal = !isDesktop && drawerOpen;
  const classes = ["sidebar", rail ? "sidebar--rail" : "", !isDesktop ? "sidebar--drawer" : "", modal ? "is-open" : ""].filter(Boolean).join(" ");

  return (
    <aside
      id="app-sidebar"
      ref={sidebarRef}
      className={classes}
      aria-label="Main navigation"
      role={modal ? "dialog" : undefined}
      aria-modal={modal ? "true" : undefined}
      inert={!isDesktop && !drawerOpen}
    >
      <div className="sidebar__header">
        {!rail && <NavLink to="/home" className="sidebar__brand" onClick={onNavigate}>TravelSync</NavLink>}
        {isDesktop ? (
          <button type="button" className="sidebar__toggle" onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-expanded={!collapsed} aria-controls="app-sidebar"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}
          </button>
        ) : (
          <button type="button" className="sidebar__toggle" onClick={onCloseDrawer} ref={closeButtonRef} aria-label="Close menu">
            <X size={20} />
          </button>
        )}
      </div>

      <nav className="sidebar__nav" aria-label="Primary">
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.label} to={item.to} className={linkClass(item)} onClick={onNavigate}
            aria-label={rail ? item.label : undefined} title={rail ? item.label : undefined}>
            <item.icon size={19} strokeWidth={1.8} aria-hidden="true" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar__footer">
        <NavLink to="/profile" className={linkClass({})} onClick={onNavigate} aria-label={rail ? "Profile" : undefined} title={rail ? "Profile" : undefined}>
          <User size={19} strokeWidth={1.8} aria-hidden="true" /><span>Profile</span>
        </NavLink>
        <NavLink to="/settings" className={linkClass({})} onClick={onNavigate} aria-label={rail ? "Settings" : undefined} title={rail ? "Settings" : undefined}>
          <Settings size={19} strokeWidth={1.8} aria-hidden="true" /><span>Settings</span>
        </NavLink>
        <button type="button" className="sidebar__nav-item sidebar__logout" onClick={handleLogout}
          aria-label={rail ? "Log out" : undefined} title={rail ? "Log out" : undefined}>
          <LogOut size={19} strokeWidth={1.8} aria-hidden="true" /><span>Log Out</span>
        </button>
      </div>
    </aside>
  );
}
