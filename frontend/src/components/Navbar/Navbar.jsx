import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Menu, X } from "lucide-react";
import "./Navbar.css";

// Reusable public navbar used on the Landing page.
// Nav links scroll to landing-page sections by id.
export default function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();

  const navLinks = [
    { label: "Home", href: "#top" },
    { label: "Explore", href: "#recommend-preview" },
    { label: "Features", href: "#features" },
    { label: "About Us", href: "#about" },
  ];

  function handleLinkClick() {
    setIsMenuOpen(false);
  }

  return (
    <header className="navbar">
      <div className="navbar__inner">
        <Link to="/" className="navbar__brand">
          TravelSync
        </Link>

        <nav className={`navbar__links ${isMenuOpen ? "navbar__links--open" : ""}`}>
          {navLinks.map((link) => (
            <a key={link.label} href={link.href} className="navbar__link" onClick={handleLinkClick}>
              {link.label}
            </a>
          ))}

          {/* Auth actions shown inline within the mobile menu too */}
          <div className="navbar__auth navbar__auth--mobile">
            <button className="navbar__login" onClick={() => navigate("/login")}>
              Log In
            </button>
            <button className="navbar__cta" onClick={() => navigate("/signup")}>
              Get Started
            </button>
          </div>
        </nav>

        <div className="navbar__auth navbar__auth--desktop">
          <button className="navbar__login" onClick={() => navigate("/login")}>
            Log In
          </button>
          <button className="navbar__cta" onClick={() => navigate("/signup")}>
            Get Started
          </button>
        </div>

        <button
          className="navbar__toggle"
          onClick={() => setIsMenuOpen((open) => !open)}
          aria-label={isMenuOpen ? "Close menu" : "Open menu"}
          aria-expanded={isMenuOpen}
        >
          {isMenuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
    </header>
  );
}