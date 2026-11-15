import { Link } from "react-router-dom";
import "./FeatureCard.css";

// Generic feature card used in the Landing page's features grid. The whole card is a link to `to`.
// `accentColor` should be one of the pastel CSS variables (e.g. "var(--pastel-blue)").
export default function FeatureCard({ icon: Icon, title, description, accentColor, to, state }) {
  return (
    <Link to={to} state={state} className="feature-card">
      <div className="feature-card__badge" style={{ backgroundColor: accentColor }}>
        <Icon size={20} strokeWidth={1.75} />
      </div>
      <h3 className="feature-card__title">{title}</h3>
      <p className="feature-card__description">{description}</p>
    </Link>
  );
}