import { useEffect, useState } from "react";
import { getDestinationProfile } from "../../services/recommendationApi";
import "./TopPlaces.css";

const inr = (value) => `₹${Number(value).toLocaleString("en-IN")}`;

// Overview of a destination from the TravelSync dataset: where it is, typical stay and daily budget, what it is known
// for and who it suits. `children` (optional) is shown under the facts, e.g. what a group member said about it.
export default function DestinationOverview({ destination, children }) {
  // The result remembers which destination it belongs to, so a different destination counts as "loading".
  const [result, setResult] = useState({ destination: null, profile: null, error: "" });

  useEffect(() => {
    if (!destination) return undefined;
    const controller = new AbortController();
    getDestinationProfile(destination, controller.signal)
      .then((data) => setResult({ destination, profile: data.destination, error: "" }))
      .catch((err) => { if (!controller.signal.aborted) setResult({ destination, profile: null, error: err.message || "Destination details could not be loaded." }); });
    return () => controller.abort();
  }, [destination]);

  if (!destination) return null;
  const settled = result.destination === destination;
  const profile = settled ? result.profile : null;

  return (
    <section className="destination-overview" aria-live="polite">
      <span className="section-kicker">DESTINATION</span>
      <h2>{destination}</h2>
      {profile && <p className="destination-overview__where">{profile.state} · {profile.region} India</p>}
      {!settled && <p className="destination-overview__where" role="status">Loading details…</p>}
      {settled && result.error && <p className="destination-overview__where" role="alert">{result.error}</p>}

      {profile && (
        <>
          <dl className="destination-overview__stats">
            <div><dt>Ideal stay</dt><dd>{profile.ideal_days} {profile.ideal_days === 1 ? "day" : "days"}</dd></div>
            <div><dt>Average daily budget</dt><dd>{inr(profile.avg_daily_budget_inr)}</dd></div>
          </dl>
          {profile.known_for.length > 0 && (
            <div className="destination-overview__row"><span>Known for</span>{profile.known_for.map((item) => <b key={item} className="place-tag place-tag--aqua">{item}</b>)}</div>
          )}
          {profile.best_for.length > 0 && (
            <div className="destination-overview__row"><span>Great for</span>{profile.best_for.map((item) => <b key={item} className="place-tag place-tag--lavender">{item}</b>)}</div>
          )}
        </>
      )}
      {children}
    </section>
  );
}
