import { Link, useNavigate } from "react-router-dom";
import { Home, Compass, Briefcase, Users, Ticket, Backpack, BedDouble, HeartPulse,User, Settings, LogOut } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import "./Sidebar.css";

// Reusable sidebar for the logged-in dashboard area.
// Future TravelSync pages (Packing, Health, AI Assistant, etc.)
// can reuse this same component once they're built.
export default function Sidebar() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const navItems = [
    { label: "Home", icon: Home, to: "/home" },
    { label: "Explore", icon: Compass, to: "#" },
    { label: "My Trips", icon: Briefcase, to: "#" },
    { label: "Packing", icon: Backpack, to: "/packing" },
    { label: "Health", icon: HeartPulse, to: "/health" },
    { label: "Groups", icon: Users, to: "#" },
    { label: "Stays", icon: BedDouble, to: "/stays" },
    { label: "Bookings", icon: Ticket, to: "#" },
  ];

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <aside className="sidebar">
      <Link to="/home" className="sidebar__brand">
        TravelSync
      </Link>

      <nav className="sidebar__nav">
        {navItems.map((item) => (
          <Link key={item.label} to={item.to} className="sidebar__nav-item">
            <item.icon size={19} strokeWidth={1.8} />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="sidebar__footer">
        <Link to="#" className="sidebar__nav-item">
          <User size={19} strokeWidth={1.8} />
          <span>Profile</span>
        </Link>
        <Link to="#" className="sidebar__nav-item">
          <Settings size={19} strokeWidth={1.8} />
          <span>Settings</span>
        </Link>
        <button className="sidebar__nav-item sidebar__logout" onClick={handleLogout}>
          <LogOut size={19} strokeWidth={1.8} />
          <span>Log Out</span>
        </button>
      </div>
    </aside>
  );
}