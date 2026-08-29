import { useNavigate } from "react-router-dom";
import { MapPin, Sparkles, Search, Bell } from "lucide-react";
import Sidebar from "../../components/Sidebar/Sidebar";
import TripPathCard from "../../components/TripPathCard/TripPathCard";
import { useAuth } from "../../context/AuthContext";
import { mockTrips } from "../../data/mockTrips";
import "./Home.css";

export default function Home() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="dashboard">
      <Sidebar />

      <div className="dashboard__main">
        <header className="dashboard__topbar">
          <div className="dashboard__search">
            <Search size={17} />
            <span>Search destinations, trips...</span>
          </div>

          <div className="dashboard__topbar-right">
            <button className="dashboard__icon-btn" aria-label="Notifications">
              <Bell size={19} />
            </button>
            <div className="dashboard__avatar">{user?.name?.charAt(0).toUpperCase()}</div>
          </div>
        </header>

        <main className="dashboard__content">
          <h1 className="dashboard__greeting">Where are we going next, {user?.name}? ✈️</h1>
          <p className="dashboard__subgreeting">Let's plan your perfect trip.</p>

          <div className="dashboard__path-cards">
            <TripPathCard
              icon={MapPin}
              title="I know my destination"
              description="Explore places, hotels, weather and more for a destination you already have in mind."
              ctaLabel="Continue →"
              accentColor="var(--pastel-blue)"
              onClick={() => navigate("/planner/select-destination")}
            />
            <TripPathCard
              icon={Sparkles}
              title="Help me find one"
              description="Tell us your travel preferences and we'll recommend destinations that match your trip."
              ctaLabel="Let's Find It ✨"
              accentColor="var(--pastel-pink)"
              onClick={() => navigate("/planner/recommend")}
            />
          </div>

          <section className="dashboard__trips">
            <h2>Your Upcoming Trips</h2>
            <div className="dashboard__trips-grid">
              {mockTrips.map((trip) => (
                <div key={trip.id} className="trip-chip" style={{ backgroundColor: trip.accentColor }}>
                  <span className="trip-chip__destination">{trip.destination}</span>
                  <span className="trip-chip__dates">{trip.dateRange}</span>
                </div>
              ))}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}