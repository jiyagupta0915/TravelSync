import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import MapExplorer from "../../components/TripMap/MapExplorer";
import { useResource } from "./useResource";
import { getTripMap } from "../../services/mapApi";
import "../Packing/Packing.css"; // reuses the "back" link style

// The full-page version of the map. The same map is also available as the floating panel on every page.
export default function TripMapPage() {
  const { tripId } = useParams();
  const navigate = useNavigate();
  // Only used for the page title; MapExplorer loads (and shows errors for) the same data itself.
  const { data } = useResource(`title:${tripId}`, () => getTripMap(tripId));

  return (
    <main className="dashboard__content">
      <button className="packing-back" onClick={() => navigate(`/trip/${tripId}`)}>
        <ArrowLeft size={16} /> Back to trip
      </button>
      <div className="dashboard__welcome">
        <div>
          <span className="dashboard__eyebrow">TRIP MAP</span>
          <h1 className="dashboard__greeting">{data ? `${data.destination} on the map 🗺️` : "Trip map 🗺️"}</h1>
          <p className="dashboard__subgreeting">See your top places and stays together, and how far they are from you. Tap a pin or a list item to focus it.</p>
        </div>
      </div>
      <MapExplorer tripId={tripId} />
    </main>
  );
}