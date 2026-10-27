import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Briefcase, CalendarDays, Trash2, WalletCards } from "lucide-react";
import Sidebar from "../../components/Sidebar/Sidebar";
import DeleteTripDialog from "../../components/DeleteTripDialog/DeleteTripDialog";
import { getTrips } from "../../services/tripApi";
import { formatTripDates } from "./tripFormat";
import "../Packing/Packing.css"; // reuses the "back" link style
import "./Trips.css";

const TONES = ["blue", "aqua", "peach"];

export default function MyTrips() {
  const navigate = useNavigate();
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tripToDelete, setTripToDelete] = useState(null);

  useEffect(() => {
    let active = true;
    getTrips()
      .then((data) => active && setTrips(data.trips || []))
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  function handleDeleted(trip) {
    setTrips((prev) => prev.filter((t) => t.id !== trip.id));
    setTripToDelete(null);
  }

  return (
    <div className="dashboard">
      <Sidebar />
      <div className="dashboard__main">
        <main className="dashboard__content">
          <div className="dashboard__welcome">
            <div>
              <span className="dashboard__eyebrow">MY TRIPS</span>
              <h1 className="dashboard__greeting">All your trips 🧳</h1>
              <p className="dashboard__subgreeting">
                Open a trip to see its packing list, shortlisted stays and health &amp; safety information in one place.
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
              <p>Choose a destination or get recommendations to create your first trip.</p>
              <button className="btn btn--primary" onClick={() => navigate("/home")}>Start planning</button>
            </div>
          ) : (
            <ul className="mytrip-grid">
              {trips.map((trip, index) => (
                <li key={trip.id} className={`mytrip-card mytrip-card--${TONES[index % TONES.length]}`}>
                  <button type="button" className="mytrip-card__open" onClick={() => navigate(`/trip/${trip.id}`)}>
                    <span className="mytrip-card__destination">{trip.destination}</span>
                    <span className="mytrip-card__meta">
                      {trip.state} · {trip.duration ? `${trip.duration}-day plan` : "Duration not set"}
                    </span>
                    {trip.budget && (
                      <span className="mytrip-card__budget"><WalletCards size={14} /> ₹{Number(trip.budget).toLocaleString("en-IN")}</span>
                    )}
                    <span className="mytrip-card__meta">{formatTripDates(trip)}</span>
                    <span className="mytrip-card__cta"><Briefcase size={14} /> Open trip space →</span>
                  </button>
                  <button
                    type="button"
                    className="mytrip-card__delete"
                    onClick={() => setTripToDelete(trip)}
                    aria-label={`Delete trip to ${trip.destination}`}
                    title="Delete trip"
                  >
                    <Trash2 size={16} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </main>
      </div>

      {tripToDelete && (
        <DeleteTripDialog key={tripToDelete.id} trip={tripToDelete} onClose={() => setTripToDelete(null)} onDeleted={handleDeleted} />
      )}
    </div>
  );
}