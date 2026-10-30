import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, Backpack, BedDouble, CalendarDays, HeartPulse, MapPin, Star, Ticket, Trash2, Users, WalletCards,
} from "lucide-react";
import DeleteTripDialog from "../../components/DeleteTripDialog/DeleteTripDialog";
import TopPlacesModal from "../../components/TopPlaces/TopPlacesModal";
import { getTrip } from "../../services/tripApi";
import { listBookings } from "../../services/bookingApi";
import { getPackingList } from "../../services/packingApi";
import { getSavedStays, removeSavedStay } from "../../services/stayApi";
import { getTravelHealth } from "../../services/healthApi";
import { formatDate, formatTripDates } from "./tripFormat";
import { useResource } from "./useResource";
import "../Packing/Packing.css"; // reuses the "back" link style
import "./Trips.css";

function formatInr(value) {
  return `₹${Number(value).toLocaleString("en-IN")}`;
}

function HubCard({ icon: Icon, tone, title, children, footer }) {
  return (
    <section className={`hub-card hub-card--${tone}`}>
      <div className="hub-card__header">
        <div className="hub-card__icon"><Icon size={20} strokeWidth={1.75} /></div>
        <h2>{title}</h2>
      </div>
      <div className="hub-card__body">{children}</div>
      {footer && <div className="hub-card__footer">{footer}</div>}
    </section>
  );
}

function PackingSummary({ tripId }) {
  const { loading, data, error } = useResource(tripId, () => getPackingList(tripId));
  const noList = /no packing list/i.test(error);

  let body;
  if (loading) body = <p className="hub-muted">Loading…</p>;
  else if (data) {
    const items = data.packing_list.items || [];
    const packed = items.filter((item) => item.packed).length;
    const pct = items.length ? Math.round((packed / items.length) * 100) : 0;
    body = (
      <>
        <p className="hub-stat"><strong>{packed}</strong> of {items.length} items packed</p>
        <div className="hub-progress"><div style={{ width: `${pct}%` }} /></div>
        <p className="hub-muted">
          {data.packing_list.tier === "forecast"
            ? `Based on the weather forecast (${data.packing_list.weather_summary}).`
            : "Based on the destination's climate. Add exact dates to refine it with a forecast."}
        </p>
      </>
    );
  } else if (noList) body = <p className="hub-muted">No packing list yet. We'll build one from the destination's climate.</p>;
  else body = <p className="hub-muted">{error}</p>;

  return (
    <HubCard
      icon={Backpack}
      tone="aqua"
      title="Packing"
      footer={<Link className="hub-link" to={`/trip/${tripId}/packing`}>{data ? "Open packing list" : "Create packing list"} →</Link>}
    >
      {body}
    </HubCard>
  );
}

function StaysSummary({ tripId }) {
  const { loading, data, error, update } = useResource(`${tripId}:stays`, () => getSavedStays(tripId));
  const [removing, setRemoving] = useState({});
  const [actionError, setActionError] = useState("");
  const saved = data?.saved || [];

  async function remove(stay) {
    setActionError("");
    setRemoving((prev) => ({ ...prev, [stay.key]: true }));
    try {
      await removeSavedStay(tripId, stay.key);
      update((prev) => ({ ...prev, saved: (prev?.saved || []).filter((s) => s.key !== stay.key) }));
    } catch (err) {
      setActionError(err.message);
    } finally {
      setRemoving((prev) => {
        const next = { ...prev };
        delete next[stay.key];
        return next;
      });
    }
  }

  let body;
  if (loading) body = <p className="hub-muted">Loading…</p>;
  else if (error) body = <p className="hub-muted">Couldn't load your shortlist right now.</p>;
  else if (saved.length === 0) body = <p className="hub-muted">No stays shortlisted yet. We'll recommend places near the destination's top spots.</p>;
  else {
    body = (
      <ul className="hub-stays">
        {saved.map((stay) => (
          <li key={stay.key}>
            <div>
              <b>{stay.name}</b>
              <small>
                {stay.type_label}{stay.stars ? ` · ${stay.stars}★` : ""} · {formatInr(stay.price_low_inr)}–{formatInr(stay.price_high_inr)} per {stay.price_unit} (estimate)
              </small>
            </div>
            <button
              type="button"
              onClick={() => remove(stay)}
              disabled={Boolean(removing[stay.key])}
              aria-label={`Remove ${stay.name} from trip`}
              title="Remove from trip"
            >
              <Trash2 size={15} />
            </button>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <HubCard
      icon={BedDouble}
      tone="peach"
      title="Shortlisted stays"
      footer={<Link className="hub-link" to={`/trip/${tripId}/stays`}>{saved.length ? "Find more stays" : "Find stays"} →</Link>}
    >
      {body}
      {actionError && <p className="hub-error" role="alert">{actionError}</p>}
    </HubCard>
  );
}

function BookingsSummary({ tripId }) {
  const { data, loading, error } = useResource(`bookings:${tripId}`, () => listBookings(tripId));
  const bookings = data?.bookings || [];
  let body;
  if (loading) body = <p className="hub-muted">Loading…</p>;
  else if (error) body = <p className="hub-muted">{error}</p>;
  else if (bookings.length === 0) body = <p className="hub-muted">No bookings recorded yet. Keep your hotel, flight, train, bus and activity details for this trip in one place.</p>;
  else {
    body = (
      <ul className="hub-list">
        {bookings.slice(0, 3).map((b) => (
          <li key={b.id}><strong>{b.title}</strong><span className="hub-muted"> · {b.kind}{b.start_date ? ` · ${formatDate(b.start_date)}` : ""}</span></li>
        ))}
        {bookings.length > 3 && <li className="hub-muted">+ {bookings.length - 3} more</li>}
      </ul>
    );
  }
  return (
    <HubCard icon={Ticket} tone="lavender" title="Bookings & tickets"
      footer={<Link className="hub-link" to={`/bookings?trip=${tripId}`}>{bookings.length ? "Manage bookings" : "Add a booking"} →</Link>}>
      {body}
    </HubCard>
  );
}

function HealthSummary({ trip }) {
  const month = trip.start_date ? new Date(trip.start_date).getMonth() + 1 : null;
  const { loading, data, error } = useResource(`${trip.destination}:${month}`, () => getTravelHealth(trip.destination, month));

  let body;
  if (loading) body = <p className="hub-muted">Loading…</p>;
  else if (error) body = <p className="hub-muted">Couldn't load health information right now.</p>;
  else {
    const active = data.current_alerts?.active || [];
    const mix = (data.disease_mix || []).slice(0, 2).map((item) => item.label);
    body = (
      <>
        {active.length > 0 ? (
          <ul className="hub-alerts">
            {active.slice(0, 2).map((alert) => (
              <li key={alert.title}><span className={`hub-severity hub-severity--${alert.severity}`}>{alert.severity}</span> {alert.title}</li>
            ))}
          </ul>
        ) : (
          <p className="hub-muted">No active alerts are listed for this state. That doesn't mean there is no risk.</p>
        )}
        {mix.length > 0 && <p className="hub-muted">Most reported outbreaks historically: {mix.join(", ")}.</p>}
        {data.is_synthetic && <p className="hub-note">The outbreak data shown is demo data.</p>}
      </>
    );
  }

  return (
    <HubCard
      icon={HeartPulse}
      tone="pink"
      title="Health & safety"
      footer={<Link className="hub-link" to={`/health?destination=${encodeURIComponent(trip.destination)}`}>Open health &amp; safety →</Link>}
    >
      {body}
    </HubCard>
  );
}

export default function TripHub() {
  const { tripId } = useParams();
  const navigate = useNavigate();
  const [showPlaces, setShowPlaces] = useState(false);
  const [showDelete, setShowDelete] = useState(false);

  // A 404 (deleted trip, or someone else's) becomes {trip: null} so the friendly "couldn't find this trip" screen shows.
  const tripsResource = useResource(`trip:${tripId}`, () => getTrip(tripId).catch((err) => {
    if (err.kind === "notfound") return { trip: null };
    throw err;
  }));
  const trip = tripsResource.data?.trip || null;

  let content;
  if (tripsResource.loading) {
    content = <div className="dashboard__empty" role="status">Loading your trip…</div>;
  } else if (tripsResource.error) {
    content = <div className="dashboard__empty dashboard__empty--error" role="alert">{tripsResource.error}</div>;
  } else if (!trip) {
    content = (
      <div className="dashboard__empty">
        <h3>We couldn't find this trip</h3>
        <p>It may have been deleted.</p>
        <button className="btn btn--primary" onClick={() => navigate("/trips")}>Back to my trips</button>
      </div>
    );
  } else {
    content = (
      <>
        <div className="hub-header">
          <div>
            <span className="dashboard__eyebrow">YOUR TRIP SPACE</span>
            <h1 className="dashboard__greeting">{trip.destination}</h1>
            <div className="hub-chips">
              <span><MapPin size={14} /> {trip.state}{trip.region ? ` · ${trip.region}` : ""}</span>
              <span><CalendarDays size={14} /> {trip.duration ? `${trip.duration}-day plan` : "Duration not set"} · {formatTripDates(trip)}</span>
              {trip.budget && <span><WalletCards size={14} /> {formatInr(trip.budget)}</span>}
              {trip.traveller_type && <span><Star size={14} /> {trip.traveller_type}</span>}
              {trip.companions?.length > 0 && <span><Users size={14} /> With {trip.companions.join(", ")}</span>}
            </div>
            {!(trip.start_date && trip.end_date) && (
              <p className="hub-muted hub-header__tip">
                Add your exact dates in <Link to={`/trip/${trip.id}/packing`}>Packing</Link> to get a weather forecast for this trip.
              </p>
            )}
          </div>
          <div className="hub-header__actions">
            <button type="button" className="hub-button" onClick={() => setShowPlaces(true)}>Top 5 places</button>
            <button type="button" className="hub-button hub-button--danger" onClick={() => setShowDelete(true)}>
              <Trash2 size={15} /> Delete trip
            </button>
          </div>
        </div>

        <div className="hub-grid">
          <PackingSummary tripId={trip.id} />
          <StaysSummary tripId={trip.id} />
          <HealthSummary trip={trip} />
          <BookingsSummary tripId={trip.id} />
        </div>

        <TopPlacesModal destination={showPlaces ? trip.destination : null} onClose={() => setShowPlaces(false)} />
        {showDelete && (
          <DeleteTripDialog key={trip.id} trip={trip} onClose={() => setShowDelete(false)} onDeleted={() => navigate("/trips")} />
        )}
      </>
    );
  }

  return (
    <main className="dashboard__content">
          <button className="packing-back" onClick={() => navigate("/trips")}>
            <ArrowLeft size={16} /> All trips
          </button>
          {content}
        </main>
  );
}