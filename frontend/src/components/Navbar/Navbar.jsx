import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Menu, X, LogOut, UserRound } from "lucide-react";
import { useAuth } from "../../context/useAuth";
import { getFirstName } from "../../utils/userDisplay";
import "./Navbar.css";

export default function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const closeMenu = () => setIsMenuOpen(false);
  const onLanding = location.pathname === "/";

  const navLinks = [
    { label: "Home", action: () => navigate(isAuthenticated ? "/home" : "/") },
    { label: "Explore", action: () => navigate(isAuthenticated ? "/planner/recommend" : "/#recommend-preview") },
    { label: "Features", action: () => onLanding ? document.getElementById("features")?.scrollIntoView({ behavior: "smooth" }) : navigate("/#features") },
    { label: "About Us", action: () => onLanding ? document.getElementById("about")?.scrollIntoView({ behavior: "smooth" }) : navigate("/#about") },
  ];

  async function handleLogout() {
    closeMenu();
    await logout();
    navigate("/");
  }

  function go(path) {
    closeMenu();
    navigate(path);
  }

  return (
    <header className="navbar">
      <div className="navbar__inner">
        <Link to={isAuthenticated ? "/home" : "/"} className="navbar__brand" onClick={closeMenu}>
          TravelSync
        </Link>

        <nav className={`navbar__links ${isMenuOpen ? "navbar__links--open" : ""}`}>
          {navLinks.map((link) => (
            <button key={link.label} type="button" className="navbar__link" onClick={() => { closeMenu(); link.action(); }}>
              {link.label}
            </button>
          ))}

          <div className="navbar__auth navbar__auth--mobile">
            {isAuthenticated ? (
              <>
                <button className="navbar__login navbar__user" onClick={() => go("/home")}>
                  <UserRound size={16} /> {getFirstName(user)}
                </button>
                <button className="navbar__cta" onClick={handleLogout}>
                  <LogOut size={16} /> Log Out
                </button>
              </>
            ) : (
              <>
                <button className="navbar__login" onClick={() => go("/login")}>Log In</button>
                <button className="navbar__cta" onClick={() => go("/signup")}>Get Started</button>
              </>
            )}
          </div>
        </nav>

        <div className="navbar__auth navbar__auth--desktop">
          {isAuthenticated ? (
            <>
              <button className="navbar__login navbar__user" onClick={() => navigate("/home")}>
                <UserRound size={16} /> {getFirstName(user)}
              </button>
              <button className="navbar__cta" onClick={handleLogout}>
                <LogOut size={16} /> Log Out
              </button>
            </>
          ) : (
            <>
              <button className="navbar__login" onClick={() => navigate("/login")}>Log In</button>
              <button className="navbar__cta" onClick={() => navigate("/signup")}>Get Started</button>
            </>
          )}
        </div>

        <button className="navbar__toggle" onClick={() => setIsMenuOpen((open) => !open)} aria-label={isMenuOpen ? "Close menu" : "Open menu"} aria-expanded={isMenuOpen}>
          {isMenuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
    </header>
  );
}
