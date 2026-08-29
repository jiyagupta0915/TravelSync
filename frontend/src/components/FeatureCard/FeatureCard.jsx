import "./FeatureCard.css";

// Generic feature card used in the Landing page's features grid.
// `accentColor` should be one of the pastel CSS variables (e.g. "var(--pastel-blue)").
export default function FeatureCard({ icon: Icon, title, description, accentColor }) {
  return (
    <article className="feature-card">
      <div className="feature-card__badge" style={{ backgroundColor: accentColor }}>
        <Icon size={20} strokeWidth={1.75} />
      </div>
      <h3 className="feature-card__title">{title}</h3>
      <p className="feature-card__description">{description}</p>
    </article>
  );
}