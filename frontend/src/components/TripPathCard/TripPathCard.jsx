import "./TripPathCard.css";

// One of the two primary path cards on the Home dashboard:
// "I know my destination" and "Help me find one".
export default function TripPathCard({ icon: Icon, title, description, ctaLabel, accentColor, onClick }) {
  return (
    <button className="trip-path-card" onClick={onClick}>
      <div className="trip-path-card__icon" style={{ backgroundColor: accentColor }}>
        <Icon size={26} strokeWidth={1.75} />
      </div>
      <h3 className="trip-path-card__title">{title}</h3>
      <p className="trip-path-card__description">{description}</p>
      <span className="trip-path-card__cta">{ctaLabel}</span>
    </button>
  );
}