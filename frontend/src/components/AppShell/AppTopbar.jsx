import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Menu, Search } from "lucide-react";
import ProfileMenu from "../ProfileMenu/ProfileMenu";
import NotificationsBell from "../NotificationsBell/NotificationsBell";

export default function AppTopbar({ showMenuButton, menuOpen, onOpenMenu, menuButtonRef }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  function handleSearch(event) {
    event.preventDefault();
    const text = query.trim();
    if (!text) return;
    // Real search: opens the destination finder with the text pre-filled.
    navigate(`/planner/select-destination?q=${encodeURIComponent(text)}`);
    setQuery("");
  }

  return (
    <header className="dashboard__topbar">
      <div className="dashboard__topbar-left">
        {showMenuButton && (
          <button type="button" ref={menuButtonRef} className="dashboard__icon-btn dashboard__menu-btn" onClick={onOpenMenu}
            aria-label="Open menu" aria-expanded={menuOpen} aria-controls="app-sidebar">
            <Menu size={21} />
          </button>
        )}
        <form className="dashboard__search" role="search" onSubmit={handleSearch}>
          <Search size={17} aria-hidden="true" />
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search destinations…" aria-label="Search destinations" maxLength={100} />
        </form>
      </div>
      <div className="dashboard__topbar-right">
        <NotificationsBell />
        <ProfileMenu />
      </div>
    </header>
  );
}
