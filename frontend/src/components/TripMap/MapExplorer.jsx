import { useMemo, useState } from "react";
import { BedDouble, LocateFixed, MapPin, Star } from "lucide-react";
import TripMap from "./TripMap";
import { buildMarkers } from "./mapMarkers";
import { getDriveDistances, getTripMap } from "../../services/mapApi";
import { getTripStays } from "../../services/stayApi";
import { useGeolocation } from "../../hooks/useGeolocation";
import { useResource } from "../../pages/Trips/useResource";
import "./MapExplorer.css";

const INDIA_CENTER = { lat: 22.6, lon: 79.0 };

// Everything inside the map UI: layer toggles, "Show my location", the map, the list of pins, legend and credits.
// It is used by the full-page map (/trip/:id/map) and by the floating map panel, so both behave identically.
//   tripId   the trip to show, or null for the plain India map (used when you have no trips yet)
//   compact  smaller layout for the floating panel
export default function MapExplorer({ tripId = null, compact = false }) {
  const [showPlaces, setShowPlaces] = useState(true);
  const [showSaved, setShowSaved] = useState(true);
  const [showSuggested, setShowSuggested] = useState(false);
  const [selected, setSelected] = useState({ scope: null, id: null });
  const geo = useGeolocation();
  const position = geo.position;
  const scope = tripId || "none";

  const mapRes = useResource(`map:${scope}`, () => getTripMap(tripId), Boolean(tripId));
  // Live stay suggestions are fetched only when that layer is switched on (it may use a Geoapify request).
  const suggestedRes = useResource(`suggested:${scope}`, () => getTripStays(tripId), Boolean(tripId) && showSuggested);
  // Driving distances are fetched only once the user has shared their location.
  const distKey = position ? `dist:${scope}:${position.lat}:${position.lon}` : "dist:none";
  const distRes = useResource(distKey, () => getDriveDistances(tripId, position), Boolean(tripId && position && mapRes.data));

  const data = mapRes.data;
  const drive = distRes.data && distRes.data.source !== "unavailable" ? distRes.data.distances : null;
  const straightLineOnly = Boolean(position && tripId && data && !distRes.loading && !drive);
  const selectedId = selected.scope === scope ? selected.id : null;

  const { markers, unlocated } = useMemo(
    () => buildMarkers({ data, showPlaces, showSaved, suggested: showSuggested ? suggestedRes.data?.stays || null : null, position, drive }),
    [data, showPlaces, showSaved, showSuggested, suggestedRes.data, position, drive],
  );

  function select(id) {
    setSelected((previous) => ({ scope, id: previous.scope === scope && previous.id === id ? null : id }));
  }

  const tripBlocked = tripId && (mapRes.loading || mapRes.error);
  const center = data ? data.center : INDIA_CENTER;

  return (
    <div className={`tmap-explorer${compact ? " tmap-explorer--compact" : ""}`}>
      {tripId && data && (
        <div className="tmap-toggles" role="group" aria-label="Map layers">
          <label className={showPlaces ? "is-on" : ""}>
            <input type="checkbox" checked={showPlaces} onChange={(e) => setShowPlaces(e.target.checked)} />
            <MapPin size={14} /> Top places
          </label>
          <label className={showSaved ? "is-on" : ""}>
            <input type="checkbox" checked={showSaved} onChange={(e) => setShowSaved(e.target.checked)} />
            <Star size={14} /> My stays ({data.saved_stays.length})
          </label>
          <label className={showSuggested ? "is-on" : ""}>
            <input type="checkbox" checked={showSuggested} onChange={(e) => setShowSuggested(e.target.checked)} />
            <BedDouble size={14} /> Suggested stays
          </label>
        </div>
      )}

      <div className="tmap-locate">
        {geo.status === "located" ? (
          <>
            <span className="tmap-locate__on"><LocateFixed size={15} /> Your location is on the map</span>
            <button type="button" className="tmap-link" onClick={geo.clear}>Hide my location</button>
          </>
        ) : (
          <>
            <button type="button" className="tmap-locate__button" onClick={geo.locate} disabled={geo.status === "locating"}>
              <LocateFixed size={15} /> {geo.status === "locating" ? "Finding you…" : "Show my location"}
            </button>
            <small>
              Asked only when you press this. {tripId
                ? "It's also used, rounded to about 1 km, to work out driving times. It isn't saved to your account."
                : "It isn't saved."}
            </small>
          </>
        )}
      </div>
      {geo.status === "error" && <p className="tmap-note" role="alert">{geo.error}</p>}
      {geo.status === "located" && tripId && distRes.loading && <p className="tmap-muted">Working out driving times…</p>}
      {straightLineOnly && (
        <p className="tmap-note">Driving times aren't available right now, so distances shown are straight-line and approximate.</p>
      )}
      {showSuggested && suggestedRes.loading && <p className="tmap-muted">Finding stays near the top places…</p>}
      {showSuggested && suggestedRes.error && <p className="tmap-note" role="alert">Suggested stays couldn't be loaded: {suggestedRes.error}</p>}
      {unlocated.length > 0 && (
        <p className="tmap-note">
          {unlocated.length === data.places.length
            ? "We don't have exact locations for this destination's top places yet, so they aren't shown."
            : `No exact location for: ${unlocated.join(", ")}.`}
        </p>
      )}

      {tripBlocked ? (
        <div className={`tmap-state${mapRes.error ? " tmap-state--error" : ""}`}>{mapRes.error || "Loading the map…"}</div>
      ) : (
        <div className="tmap-layout">
          <div className="tmap-canvas">
            <TripMap center={center} markers={markers} selectedId={selectedId} onSelect={select} emptyZoom={tripId ? 11 : 5} />
          </div>

          <aside className="tmap-list" aria-label="Pins on the map">
            {markers.length === 0 ? (
              <p className="tmap-muted">{tripId ? "Nothing to show with the current layers." : "Create a trip to see its places here, or show your location."}</p>
            ) : (
              <ul>
                {markers.map((m) => (
                  <li key={m.id}>
                    <button type="button" className={selectedId === m.id ? "is-selected" : ""} onClick={() => select(m.id)}>
                      <span className={`tmap-dot tmap-dot--${m.kind}`}>{m.symbol}</span>
                      <span>
                        <b>{m.title}</b>
                        <small>{m.sub}</small>
                        {m.distance && <small className="tmap-distance">{m.distance}</small>}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      )}

      <ul className="tmap-legend">
        <li><span className="tmap-dot tmap-dot--me">●</span> You</li>
        {tripId && <li><span className="tmap-dot tmap-dot--dest">⚑</span> Destination</li>}
        {tripId && <li><span className="tmap-dot tmap-dot--place">1</span> Top place</li>}
        {tripId && <li><span className="tmap-dot tmap-dot--stay">★</span> My stay</li>}
        {tripId && showSuggested && <li><span className="tmap-dot tmap-dot--suggested">•</span> Suggested stay</li>}
      </ul>
      <p className="tmap-footnote">
        Map data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>.
        {tripId && <> Driving times and stay data powered by <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer">Geoapify</a>.</>}
        {tripId && " Stay prices are estimates, not live rates."}
      </p>
    </div>
  );
}