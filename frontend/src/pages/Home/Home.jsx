import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapPin, Sparkles, Search, Bell, CalendarDays, WalletCards, HeartPulse } from "lucide-react";
import Sidebar from "../../components/Sidebar/Sidebar";
import TripPathCard from "../../components/TripPathCard/TripPathCard";
import TopPlacesModal from "../../components/TopPlaces/TopPlacesModal";
import { useAuth } from "../../context/AuthContext";
import { getTrips } from "../../services/tripApi";
import "./Home.css";

function formatCreatedAt(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

export default function Home() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [trips, setTrips] = useState([]);
  const [loadingTrips, setLoadingTrips] = useState(true);
  const [tripError, setTripError] = useState("");
  const [placesFor, setPlacesFor] = useState(null);

  useEffect(() => {
    let active = true;
    getTrips()
      .then((data) => active && setTrips(data.trips || []))
      .catch((error) => active && setTripError(error.message))
      .finally(() => active && setLoadingTrips(false));
    return () => { active = false; };
  }, []);

  return (
    <div className="dashboard">
      <Sidebar />
      <div className="dashboard__main">
        <header className="dashboard__topbar">
          <div className="dashboard__search"><Search size={17} /><span>Search destinations, trips...</span></div>
          <div className="dashboard__topbar-right">
            <button className="dashboard__icon-btn" aria-label="Notifications"><Bell size={19} /></button>
            <div className="dashboard__avatar" title={user?.name}>{user?.name?.charAt(0).toUpperCase()}</div>
          </div>
        </header>

        <main className="dashboard__content">
          <div className="dashboard__welcome">
            <div>
              <span className="dashboard__eyebrow">YOUR TRAVEL SPACE</span>
              <h1 className="dashboard__greeting">Where are we going next, {user?.name?.split(" ")[0]}? ✈️</h1>
              <p className="dashboard__subgreeting">Start with a destination or let TravelSync help you discover one.</p>
            </div>
          </div>

          <div className="dashboard__path-cards">
            <TripPathCard icon={MapPin} title="I know my destination" description="Enter a destination you already have in mind and continue to its TravelSync trip space." ctaLabel="Choose destination →" accentColor="var(--pastel-blue)" onClick={() => navigate("/planner/select-destination")} />
            <TripPathCard icon={Sparkles} title="Help me find one" description="Tell us about your interests, budget, duration and starting point to discover suitable destinations." ctaLabel="Find a destination ✨" accentColor="var(--pastel-pink)" onClick={() => navigate("/planner/recommend")} />
          </div>

          <section className="dashboard__trips">
            <div className="dashboard__section-heading">
              <div><span className="dashboard__eyebrow">SAVED TRIPS</span><h2>Your Upcoming Trips</h2></div>
              {trips.length > 0 && <span className="dashboard__trip-count">{trips.length} {trips.length === 1 ? "trip" : "trips"}</span>}
            </div>

            {loadingTrips ? (
              <div className="dashboard__empty">Loading your trips…</div>
            ) : tripError ? (
              <div className="dashboard__empty dashboard__empty--error">{tripError}</div>
            ) : trips.length === 0 ? (
              <div className="dashboard__empty">
                <CalendarDays size={25} />
                <h3>No trips yet</h3>
                <p>Choose a destination or get recommendations to create your first trip.</p>
                <button className="btn btn--primary" onClick={() => navigate("/planner/recommend")}>Start planning</button>
              </div>
            ) : (
              <div className="dashboard__trips-grid">
                                {trips.map((trip) => (
                  <div key={trip.id} className="trip-card">
                    <button className="trip-chip" onClick={() => setPlacesFor(trip.destination)} aria-haspopup="dialog">
                      <span className="trip-chip__destination">{trip.destination}</span>
                      <span className="trip-chip__meta">{trip.state} · {trip.duration ? `${trip.duration}-day plan` : "Destination selected"}</span>
                      {trip.budget && <span className="trip-chip__budget"><WalletCards size={14} /> ₹{Number(trip.budget).toLocaleString("en-IN")}</span>}
                      <span className="trip-chip__dates">Created {formatCreatedAt(trip.created_at)}</span>
                    </button>
                    <button className="trip-card__health" onClick={() => navigate(`/health?destination=${encodeURIComponent(trip.destination)}`)}>
                      <HeartPulse size={14} /> Health &amp; safety
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </main>
      </div>
      <TopPlacesModal destination={placesFor} onClose={() => setPlacesFor(null)} />
    </div>
  );
}
