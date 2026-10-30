import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogOut, Settings, User } from "lucide-react";
import { useAuth } from "../../context/useAuth";
import { getDisplayName, getInitials } from "../../utils/userDisplay";
import "./ProfileMenu.css";

// Account dropdown for the top bar (WAI-ARIA "menu button" pattern).
//   Button: Enter / Space / ArrowDown open and focus the first item, ArrowUp opens on the last.
//   Menu  : ArrowUp/Down and Home/End move focus, Escape closes and returns focus to the button,
//           Tab closes, clicking outside closes.
export default function ProfileMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [pendingFocus, setPendingFocus] = useState("first");
  const rootRef = useRef(null);
  const buttonRef = useRef(null);
  const menuRef = useRef(null);
  const menuId = useId();

  const name = getDisplayName(user);
  const email = user?.email || "";

  const items = useCallback(() => Array.from(menuRef.current?.querySelectorAll('[role="menuitem"]') ?? []), []);

  const close = useCallback((restoreFocus = false) => {
    setOpen(false);
    if (restoreFocus) buttonRef.current?.focus();
  }, []);

  // Move focus into the menu after it opens.
  useEffect(() => {
    if (!open) return;
    const list = items();
    (pendingFocus === "last" ? list[list.length - 1] : list[0])?.focus();
  }, [open, pendingFocus, items]);

  // Outside click closes the menu.
  useEffect(() => {
    if (!open) return undefined;
    function onPointerDown(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  function openWith(which) {
    setPendingFocus(which);
    setOpen(true);
  }

  function onButtonKeyDown(event) {
    if (event.key === "ArrowDown") { event.preventDefault(); openWith("first"); }
    else if (event.key === "ArrowUp") { event.preventDefault(); openWith("last"); }
  }

  function onMenuKeyDown(event) {
    const list = items();
    const index = list.indexOf(document.activeElement);
    if (event.key === "Escape") { event.preventDefault(); close(true); }
    else if (event.key === "Tab") { close(false); }
    else if (event.key === "ArrowDown") { event.preventDefault(); list[(index + 1) % list.length]?.focus(); }
    else if (event.key === "ArrowUp") { event.preventDefault(); list[(index - 1 + list.length) % list.length]?.focus(); }
    else if (event.key === "Home") { event.preventDefault(); list[0]?.focus(); }
    else if (event.key === "End") { event.preventDefault(); list[list.length - 1]?.focus(); }
  }

  async function handleLogout() {
    close(false);
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="profile-menu" ref={rootRef}>
      <button
        type="button" ref={buttonRef} className="profile-menu__button"
        aria-haspopup="menu" aria-expanded={open} aria-controls={open ? menuId : undefined}
        aria-label={`Account menu for ${name}`}
        onClick={() => (open ? close(false) : openWith("first"))}
        onKeyDown={onButtonKeyDown}
      >
        <span className="profile-menu__avatar" aria-hidden="true">{getInitials(user)}</span>
      </button>

      {open && (
        <div className="profile-menu__panel" id={menuId} role="menu" aria-label="Account" ref={menuRef} onKeyDown={onMenuKeyDown}>
          <div className="profile-menu__identity" role="none">
            <span className="profile-menu__avatar profile-menu__avatar--large" aria-hidden="true">{getInitials(user)}</span>
            <div>
              <p className="profile-menu__name">{name}</p>
              {email && <p className="profile-menu__email">{email}</p>}
            </div>
          </div>
          <Link to="/profile" role="menuitem" tabIndex={-1} className="profile-menu__item" onClick={() => close(false)}><User size={17} aria-hidden="true" /> Profile</Link>
          <Link to="/settings" role="menuitem" tabIndex={-1} className="profile-menu__item" onClick={() => close(false)}><Settings size={17} aria-hidden="true" /> Settings</Link>
          <button type="button" role="menuitem" tabIndex={-1} className="profile-menu__item profile-menu__item--danger" onClick={handleLogout}><LogOut size={17} aria-hidden="true" /> Log out</button>
        </div>
      )}
    </div>
  );
}
