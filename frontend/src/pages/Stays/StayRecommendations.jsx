import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, ExternalLink, MapPin, Navigation, Phone, Star, Wallet } from "lucide-react";
import Sidebar from "../../components/Sidebar/Sidebar";
import { getTripStays } from "../../services/stayApi";
import "../Packing/Packing.css"; // reuses the "back" link style
import "./Stays.css";

const PAGE_SIZE = 6;

const BUDGET_LABELS = {
  within: "Within budget",
  slightly_above: "Slightly above budget",
  above: "Above budget",
};

function formatInr(value) {
  return `₹${Number(value).toLocaleString("en-IN")}`;
}

function StayCard({ stay, index }) {
  const phoneHref = stay.phone ? `tel:${String(stay.phone).replace(/[^+\d]/g, "")}` : null;
  return (
    <li className="stay-card">
      <div className="stay-card__top">
        <span className="stay-card__rank">{String(index + 1).padStart(2, "0")}</span>
        <span className={`stay-tag stay-tag--${stay.type}`}>{stay.type_label}</span>
        <span className="stay-card__match">{stay.match_percent}% match</span>
      </div>

      <h3 className="stay-card__name">{stay.name}</h3>
      <p className="stay-card__address">
        {stay.stars ? <span className="stay-card__stars"><Star size={13} fill="currentColor" /> {stay.stars}</span> : null}
        {stay.address && <span><MapPin size={13} /> {stay.address}</span>}
      </p>

      <ul className="stay-card__reasons">
        {stay.reasons.map((reason) => (
          <li key={reason}><Check size={14} /> {reason}</li>
        ))}
      </ul>

      <p className="stay-card__nearest">
        <Navigation size={13} /> {stay.nearest_place_km} km from {stay.nearest_place}
      </p>

      <div className="stay-card__price">
        <div>
          <strong>{formatInr(stay.price_low_inr)} – {formatInr(stay.price_high_inr)}</strong>
          <span> per {stay.price_unit} / night</span>
          <small className="stay-card__estimate">estimate</small>
        </div>
        <span className={`stay-fit stay-fit--${stay.budget_fit}`}><Wallet size={12} /> {BUDGET_LABELS[stay.budget_fit]}</span>
      </div>

      <div className="stay-card__actions">
        {stay.website && (
          <a href={stay.website} target="_blank" rel="noopener noreferrer"><ExternalLink size={14} /> Website</a>
        )}
        <a href={stay.maps_url} target="_blank" rel="noopener noreferrer"><MapPin size={14} /> Open in Maps</a>
        {phoneHref && <a href={phoneHref}><Phone size={14} /> Call</a>}
      </div>
    </li>
  );
}

export default function StayRecommendations() {
  const { tripId } = useParams();
  const navigate = useNavigate();

  const [result, setResult] = useState({ tripId: null, data: null, error: "" });
  const [filter, setFilter] = useState("all");
  const [visible, setVisible] = useState(PAGE_SIZE);

  useEffect(() => {
    let active = true;
    getTripStays(tripId)
      .then((data) => active && setResult({ tripId, data, error: "" }))
      .catch((err) => active && setResult({ tripId, data: null, error: err.message }));
    return () => { active = false; };
  }, [tripId]);

  // Loading until the answer for *this* trip has arrived (also covers switching between trips).
  const loading = result.tripId !== tripId;
  const data = loading ? null : result.data;
  const error = loading ? "" : result.error;

  const typeCounts = useMemo(() => {
    const counts = {};
    for (const stay of data?.stays || []) {
      counts[stay.type] = counts[stay.type] || { label: stay.type_label, count: 0 };
      counts[stay.type].count += 1;
    }
    return counts;
  }, [data]);

  const activeFilter = typeCounts[filter] ? filter : "all";
  const filtered = useMemo(
    () => (data?.stays || []).filter((stay) => activeFilter === "all" || stay.type === activeFilter),
    [data, activeFilter]
  );

  function chooseFilter(next) {
    setFilter(next);
    setVisible(PAGE_SIZE);
  }

  const usingPlaces = data?.anchor.basis === "top_places";

  return (
    <div className="dashboard">
      <Sidebar />
      <div className="dashboard__main">
        <main className="dashboard__content">
          <button className="packing-back" onClick={() => navigate("/stays")}>
            <ArrowLeft size={16} /> All trips
          </button>

          <div className="dashboard__welcome">
            <div>
              <span className="dashboard__eyebrow">SMART STAY RECOMMENDATIONS</span>
              <h1 className="dashboard__greeting">
                {data ? `Where to stay in ${data.destination} 🛏️` : "Finding places to stay 🛏️"}
              </h1>
            </div>
          </div>

          {loading && (
            <div className="stay-grid" aria-busy="true">
              {[1, 2, 3].map((n) => <div className="stay-skeleton" key={n} />)}
            </div>
          )}

          {!loading && error && <div className="dashboard__empty dashboard__empty--error">{error}</div>}

          {!loading && data && (
            <>
              <section className="stay-summary">
                <div>
                  <strong>How we ranked these</strong>
                  <p>
                    Closeness to the top places (40%), fit with your budget (30%), suitability for{" "}
                    {data.traveller_type ? data.traveller_type.toLowerCase() : "your"} travellers (20%) and listing quality (10%).
                  </p>
                </div>
                <div className="stay-summary__chips">
                  <span><Wallet size={14} /> About {formatInr(data.nightly_budget_per_person_inr)} per person per night for a stay ({data.budget_basis})</span>
                </div>
                <div className="stay-summary__places">
                  {usingPlaces ? (
                    <>
                      <span>Measured from your top places:</span>
                      {data.anchor.places.filter((p) => p.lat !== null).map((p) => (
                        <b key={p.name}>{p.rank}. {p.name}</b>
                      ))}
                    </>
                  ) : (
                    <span>Measured from the destination centre (exact place locations aren't loaded yet).</span>
                  )}
                </div>
              </section>

              <div className="stay-filters" role="tablist" aria-label="Filter by stay type">
                <button type="button" className={activeFilter === "all" ? "is-active" : ""} onClick={() => chooseFilter("all")}>
                  All ({data.stays.length})
                </button>
                {Object.entries(typeCounts).map(([type, info]) => (
                  <button key={type} type="button" className={activeFilter === type ? "is-active" : ""} onClick={() => chooseFilter(type)}>
                    {info.label} ({info.count})
                  </button>
                ))}
              </div>

              <ol className="stay-grid">
                {filtered.slice(0, visible).map((stay, index) => (
                  <StayCard stay={stay} index={index} key={`${stay.name}-${stay.lat}-${stay.lon}`} />
                ))}
              </ol>

              {visible < filtered.length && (
                <div className="stay-more">
                  <button type="button" className="btn btn--primary" onClick={() => setVisible((v) => v + PAGE_SIZE)}>
                    Show more stays
                  </button>
                </div>
              )}

              <p className="stay-footnote">
                Prices are rough estimates based on the type and star rating of each stay, not live rates, so please check the
                stay's website or call before booking. Stay data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>,
                powered by <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer">Geoapify</a>.
              </p>
            </>
          )}
        </main>
      </div>
    </div>
  );
}