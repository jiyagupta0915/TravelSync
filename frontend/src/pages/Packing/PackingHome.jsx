import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Backpack, CalendarDays, MapPin } from "lucide-react";
import Sidebar from "../../components/Sidebar/Sidebar";
import { getTrips } from "../../services/tripApi";
import "./Packing.css";

export default function PackingHome() {
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
    <div className="dashboard">
      <Sidebar />
      <div className="dashboard__main">
        <main className="dashboard__content">
          <div className="dashboard__welcome">
            <div>
              <span className="dashboard__eyebrow">SMART PACKING ASSISTANT</span>
              <h1 className="dashboard__greeting">Pick a trip to pack for 🎒</h1>
              <p className="dashboard__subgreeting">
                We'll suggest a checklist based on the destination's climate — and refine it with a real forecast once you add your travel dates.
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
              <p>Create a trip first, then come back here to build a packing list for it.</p>
              <button className="btn btn--primary" onClick={() => navigate("/home")}>Go to trips</button>
            </div>
          ) : (
            <div className="packing-trip-grid">
              {trips.map((trip) => (
                <button
                  key={trip.id}
                  className="packing-trip-card"
                  onClick={() => navigate(`/trip/${trip.id}/packing`)}
                >
                  <div className="packing-trip-card__icon"><Backpack size={22} strokeWidth={1.75} /></div>
                  <h3 className="packing-trip-card__title"><MapPin size={14} /> {trip.destination}</h3>
                  <p className="packing-trip-card__meta">
                    {trip.state} · {trip.duration ? `${trip.duration}-day plan` : "Duration not set"}
                  </p>
                  <span className="packing-trip-card__cta">Open packing list →</span>
                </button>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}