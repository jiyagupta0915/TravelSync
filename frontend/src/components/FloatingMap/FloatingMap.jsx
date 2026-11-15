import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link, useMatch } from "react-router-dom";
import { Map as MapIcon, Maximize2, X } from "lucide-react";
import { getTrips } from "../../services/tripApi";
import { useResource } from "../../pages/Trips/useResource";
import "./FloatingMap.css";

// The map (and the Leaflet library) is downloaded only the first time the panel is opened.
const MapExplorer = lazy(() => import("../TripMap/MapExplorer"));

// The floating map: a round button above every signed-in page that opens a map panel without leaving the page.
// Mounted once by AppShell, next to the assistant. Which trip it shows:
//   1. the trip chosen in the panel's drop-down, else
//   2. the trip whose page you are on (/trip/:id/...), else
//   3. your newest trip, else
//   4. nothing: a plain India map with "Show my location".
export default function FloatingMap() {
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState({ route: null, id: null });
  const launcherRef = useRef(null);
  const closeRef = useRef(null);

  const routeTripId = useMatch("/trip/:tripId/*")?.params.tripId ?? null;
  const onMapPage = Boolean(useMatch("/trip/:tripId/map"));

  const tripsRes = useResource("floating-map-trips", () => getTrips(), open);
  const trips = tripsRes.data?.trips || [];

  // A choice made in the drop-down only counts while you stay on the same page's trip.
  const chosenId = choice.route === routeTripId && trips.some((t) => t.id === choice.id) ? choice.id : null;
  const routeId = trips.some((t) => t.id === routeTripId) ? routeTripId : null;
  const tripId = chosenId || routeId || trips[0]?.id || null;

  useEffect(() => {
    if (!open) return undefined;
    closeRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === "Escape") { setOpen(false); launcherRef.current?.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  // The full-page map already is the map, so the button would only be a duplicate there.
  if (onMapPage) return null;

  const close = () => { setOpen(false); launcherRef.current?.focus(); };

  return (
    <div className={`floating-map${open ? " is-open" : ""}`}>
      {open && (
        <section className="floating-map__panel" role="dialog" aria-label="Trip map">
          <header className="floating-map__header">
            <div className="floating-map__title">
              <strong>Trip map</strong>
              {trips.length > 0 && (
                <select
                  aria-label="Choose a trip"
                  value={tripId || ""}
                  onChange={(event) => setChoice({ route: routeTripId, id: event.target.value })}
                >
                  {trips.map((trip) => (
                    <option key={trip.id} value={trip.id}>
                      {trip.destination}{trip.duration ? ` · ${trip.duration} days` : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="floating-map__actions">
              {tripId && (
                <Link to={`/trip/${tripId}/map`} onClick={() => setOpen(false)} aria-label="Open the full-page map" title="Open full page">
                  <Maximize2 size={17} />
                </Link>
              )}
              <button type="button" ref={closeRef} onClick={close} aria-label="Close map"><X size={18} /></button>
            </div>
          </header>

          <div className="floating-map__body">
            {tripsRes.loading ? (
              <p className="floating-map__status">Loading your trips…</p>
            ) : (
              <>
                {tripsRes.error && <p className="floating-map__status floating-map__status--error">Your trips couldn't be loaded, so only the general map is shown.</p>}
                {!tripsRes.error && trips.length === 0 && (
                  <p className="floating-map__status">You have no trips yet. <Link to="/planner/select-destination" onClick={() => setOpen(false)}>Create one</Link> to see its places here.</p>
                )}
                <Suspense fallback={<p className="floating-map__status">Loading the map…</p>}>
                  {/* key: switching trips starts a fresh map (and a fresh "my location" request state) */}
                  <MapExplorer key={tripId || "none"} tripId={tripId} compact />
                </Suspense>
              </>
            )}
          </div>
        </section>
      )}

      <button
        type="button"
        ref={launcherRef}
        className="floating-map__launcher"
        onClick={() => (open ? close() : setOpen(true))}
        aria-expanded={open}
        aria-label={open ? "Close map" : "Open map"}
        title="Map"
      >
        <MapIcon size={24} />
      </button>
    </div>
  );
}