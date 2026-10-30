import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Briefcase, CalendarDays, Ticket, Trash2, Users, WalletCards } from "lucide-react";
import DeleteTripDialog from "../../components/DeleteTripDialog/DeleteTripDialog";
import { getTrips } from "../../services/tripApi";
import { formatTripDates, isPreviousTrip, todayIso } from "./tripFormat";
import "../Packing/Packing.css"; // reuses the "back" link style
import "./Trips.css";

const TONES = ["blue", "aqua", "peach"];
const FILTERS = [
  { id: "all", label: "All trips" },
  { id: "upcoming", label: "Upcoming" },
  { id: "previous", label: "Previous trips" },
];

export default function MyTrips() {
  const navigate = useNavigate();
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tripToDelete, setTripToDelete] = useState(null);
  const [filter, setFilter] = useState("all");

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

  const visible = useMemo(() => {
    const today = todayIso();
    if (filter === "previous") return trips.filter((t) => isPreviousTrip(t, today));
    if (filter === "upcoming") return trips.filter((t) => !isPreviousTrip(t, today));
    return trips;
  }, [trips, filter]);

  return (
    <main className="dashboard__content">
      <div className="dashboard__welcome">
        <div>
          <span className="dashboard__eyebrow">MY TRIPS</span>
          <h1 className="dashboard__greeting">All your trips 🧳</h1>
          <p className="dashboard__subgreeting">
            Open a trip to see its packing list, shortlisted stays, bookings and health &amp; safety information in one place.
          </p>
        </div>
      </div>

      {!loading && !error && trips.length > 0 && (
        <div className="mytrip-filters" role="group" aria-label="Filter trips">
          {FILTERS.map((item) => (
            <button key={item.id} type="button" className={`mytrip-filter${filter === item.id ? " is-active" : ""}`} aria-pressed={filter === item.id} onClick={() => setFilter(item.id)}>
              {item.label}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="dashboard__empty" role="status">Loading your trips…</div>
      ) : error ? (
        <div className="dashboard__empty dashboard__empty--error" role="alert">{error}</div>
      ) : trips.length === 0 ? (
        <div className="dashboard__empty">
          <CalendarDays size={25} />
          <h3>No trips yet</h3>
          <p>Choose a destination or get recommendations to create your first trip.</p>
          <button className="btn btn--primary" onClick={() => navigate("/home")}>Start planning</button>
        </div>
      ) : visible.length === 0 ? (
        <div className="dashboard__empty">
          <CalendarDays size={25} />
          <h3>{filter === "previous" ? "No previous trips yet" : "No upcoming trips"}</h3>
          <p>
            {filter === "previous"
              ? "A trip moves here once its end date has passed. Add travel dates to a trip from its Packing assistant."
              : "Every trip you have has already ended. Plan a new one from Home."}
          </p>
        </div>
      ) : (
        <ul className="mytrip-grid">
          {visible.map((trip, index) => (
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
                {trip.companions?.length > 0 && (
                  <span className="mytrip-card__meta"><Users size={13} aria-hidden="true" /> With {trip.companions.join(", ")}</span>
                )}
                {trip.booking_count > 0 && (
                  <span className="mytrip-card__meta"><Ticket size={13} aria-hidden="true" /> {trip.booking_count} {trip.booking_count === 1 ? "booking" : "bookings"}</span>
                )}
                <span className="mytrip-card__cta"><Briefcase size={14} /> Open trip space →</span>
              </button>
              <button type="button" className="mytrip-card__delete" onClick={() => setTripToDelete(trip)} aria-label={`Delete trip to ${trip.destination}`} title="Delete trip">
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {tripToDelete && (
        <DeleteTripDialog key={tripToDelete.id} trip={tripToDelete} onClose={() => setTripToDelete(null)} onDeleted={handleDeleted} />
      )}
    </main>
  );
}
