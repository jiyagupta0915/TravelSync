import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BedDouble, CalendarDays, MapPin } from "lucide-react";
import { getTrips } from "../../services/tripApi";
import "../Packing/Packing.css"; // reuses the trip-picker card styles
import "./Stays.css";

export default function StaysHome() {
  const navigate = useNavigate();
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getTrips()
      .then((data) => active && setTrips(data.trips || []))
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  return (
    <main className="dashboard__content">
          <div className="dashboard__welcome">
            <div>
              <span className="dashboard__eyebrow">SMART STAY RECOMMENDATIONS</span>
              <h1 className="dashboard__greeting">Pick a trip to find a stay for 🛏️</h1>
              <p className="dashboard__subgreeting">
                We rank hotels, hostels and guest houses by how close they are to the destination's top places, how well they fit your budget, and who you're travelling with.
              </p>
            </div>
          </div>

          {loading ? (
            <div className="dashboard__empty">Loading your trips…</div>
          ) : error ? (
            <div className="dashboard__empty dashboard__empty--error">{error}</div>
          ) : trips.length === 0 ? (
            <div className="dashboard__empty">
              <CalendarDays size={25} />
              <h3>No trips yet</h3>
              <p>Create a trip first, then come back here to find places to stay.</p>
              <button className="btn btn--primary" onClick={() => navigate("/home")}>Go to trips</button>
            </div>
          ) : (
            <div className="packing-trip-grid">
              {trips.map((trip) => (
                <button
                  key={trip.id}
                  className="packing-trip-card"
                  onClick={() => navigate(`/trip/${trip.id}/stays`)}
                >
                  <div className="packing-trip-card__icon"><BedDouble size={22} strokeWidth={1.75} /></div>
                  <h3 className="packing-trip-card__title"><MapPin size={14} /> {trip.destination}</h3>
                  <p className="packing-trip-card__meta">
                    {trip.state} · {trip.duration ? `${trip.duration}-day plan` : "Duration not set"}
                  </p>
                  <span className="packing-trip-card__cta">Find stays →</span>
                </button>
              ))}
            </div>
          )}
        </main>
  );
}