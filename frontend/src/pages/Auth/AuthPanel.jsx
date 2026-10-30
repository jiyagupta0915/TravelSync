import { Link } from "react-router-dom";

// The decorative left-hand panel shared by every auth page.
export default function AuthPanel({ heading, text }) {
  return (
    <aside className="auth__panel">
      <Link to="/" className="auth__brand">TravelSync</Link>
      <div className="auth__panel-content">
        <h2>{heading}</h2>
        <p>{text}</p>
      </div>
      <div className="auth__panel-visual" aria-hidden="true">
        <svg viewBox="0 0 200 160" className="auth__panel-svg">
          <path d="M20 130 C 60 100, 90 110, 110 70 S 160 30, 180 15" stroke="var(--ink)" strokeWidth="2" strokeDasharray="6 9" strokeLinecap="round" fill="none" />
          <circle cx="20" cy="130" r="5" fill="var(--ink)" />
          <circle cx="180" cy="15" r="5" fill="var(--ink)" />
        </svg>
      </div>
    </aside>
  );
}
