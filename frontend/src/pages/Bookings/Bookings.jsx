import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Bed, Bus, Plane, Plus, Ticket, Trash2, Train, Pencil, Sparkles } from "lucide-react";
import NumberField from "../../components/NumberField/NumberField";
import { getTrips } from "../../services/tripApi";
import { createBooking, deleteBooking, listBookings, updateBooking } from "../../services/bookingApi";
import { parsePositiveInteger } from "../../utils/numberField";
import "../../styles/appPages.css";
import "./Bookings.css";

const KINDS = [
  { id: "hotel", label: "Hotel / stay", icon: Bed },
  { id: "flight", label: "Flight", icon: Plane },
  { id: "train", label: "Train", icon: Train },
  { id: "bus", label: "Bus", icon: Bus },
  { id: "activity", label: "Activity / ticket", icon: Sparkles },
  { id: "other", label: "Other", icon: Ticket },
];
const KIND = Object.fromEntries(KINDS.map((k) => [k.id, k]));
const EMPTY = { trip_id: "", kind: "hotel", title: "", provider: "", reference: "", start_date: "", end_date: "", amount: "", notes: "" };

const formatDate = (iso) => (iso ? new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${iso}T00:00:00`)) : "");

function BookingForm({ trips, initial, editingId, onSaved, onCancel }) {
  const [form, setForm] = useState(initial);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const set = (key) => (e) => { setForm((f) => ({ ...f, [key]: e.target.value })); setErrors((er) => ({ ...er, [key]: undefined })); };

  async function handleSubmit(event) {
    event.preventDefault();
    if (saving) return;
    const next = {};
    if (!form.trip_id) next.trip_id = "Choose which trip this belongs to.";
    if (!form.title.trim()) next.title = "Give this booking a title.";
    if (form.start_date && form.end_date && form.end_date < form.start_date) next.end_date = "The end date can't be earlier than the start date.";
    let amount = null;
    if (form.amount !== "") {
      const parsed = parsePositiveInteger(form.amount, { label: "the amount", min: 0, max: 100_000_000 });
      if (parsed.ok) amount = parsed.value; else next.amount = parsed.error;
    }
    setErrors(next); setFormError("");
    if (Object.keys(next).length) return;

    const body = {
      kind: form.kind, title: form.title.trim(), provider: form.provider.trim(), reference: form.reference.trim(),
      start_date: form.start_date || null, end_date: form.end_date || null, amount_inr: amount, notes: form.notes.trim(),
    };
    setSaving(true);
    try {
      const { booking } = editingId ? await updateBooking(editingId, body) : await createBooking({ ...body, trip_id: form.trip_id });
      onSaved(booking);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="ts-card" onSubmit={handleSubmit} noValidate aria-label={editingId ? "Edit booking" : "Add a booking"}>
      <h2>{editingId ? "Edit booking" : "Add a booking"}</h2>
      <p className="ts-muted">Record a reservation you made elsewhere. TravelSync keeps your details in one place; it doesn't book or confirm anything for you.</p>
      <div className="ts-form ts-form--wide">
        <div className="ts-field">
          <label htmlFor="bk-trip">Trip</label>
          <select id="bk-trip" value={form.trip_id} onChange={set("trip_id")} disabled={Boolean(editingId)} aria-invalid={Boolean(errors.trip_id) || undefined}>
            <option value="">Select a trip…</option>
            {trips.map((t) => <option key={t.id} value={t.id}>{t.destination}{t.duration ? ` · ${t.duration} days` : ""}</option>)}
          </select>
          {errors.trip_id && <span className="ts-error" role="alert">{errors.trip_id}</span>}
        </div>
        <div className="ts-field">
          <label htmlFor="bk-kind">Type</label>
          <select id="bk-kind" value={form.kind} onChange={set("kind")}>{KINDS.map((k) => <option key={k.id} value={k.id}>{k.label}</option>)}</select>
        </div>
        <div className="ts-field">
          <label htmlFor="bk-title">Title</label>
          <input id="bk-title" value={form.title} maxLength={100} onChange={set("title")} placeholder="e.g. Taj Resort, DEL → GOI" aria-invalid={Boolean(errors.title) || undefined} />
          {errors.title && <span className="ts-error" role="alert">{errors.title}</span>}
        </div>
        <div className="ts-field">
          <label htmlFor="bk-provider">Provider <span className="ts-hint">(optional)</span></label>
          <input id="bk-provider" value={form.provider} maxLength={80} onChange={set("provider")} />
        </div>
        <div className="ts-field">
          <label htmlFor="bk-ref">Confirmation / ticket number <span className="ts-hint">(optional)</span></label>
          <input id="bk-ref" value={form.reference} maxLength={60} onChange={set("reference")} autoComplete="off" />
        </div>
        <div className="ts-field">
          <label htmlFor="bk-amount">Amount paid <span className="ts-hint">(optional)</span></label>
          <div className="ts-input-unit"><b>₹</b><NumberField id="bk-amount" value={form.amount} maxLength={9} onChange={(v) => { setForm((f) => ({ ...f, amount: v })); setErrors((er) => ({ ...er, amount: undefined })); }} invalid={Boolean(errors.amount)} /></div>
          {errors.amount && <span className="ts-error" role="alert">{errors.amount}</span>}
        </div>
        <div className="ts-field">
          <label htmlFor="bk-start">Start date</label>
          <input id="bk-start" type="date" value={form.start_date} onChange={set("start_date")} />
        </div>
        <div className="ts-field">
          <label htmlFor="bk-end">End date</label>
          <input id="bk-end" type="date" value={form.end_date} min={form.start_date || undefined} onChange={set("end_date")} aria-invalid={Boolean(errors.end_date) || undefined} />
          {errors.end_date && <span className="ts-error" role="alert">{errors.end_date}</span>}
        </div>
        <div className="ts-field" style={{ gridColumn: "1 / -1" }}>
          <label htmlFor="bk-notes">Notes <span className="ts-hint">(optional)</span></label>
          <textarea id="bk-notes" value={form.notes} maxLength={500} onChange={set("notes")} />
        </div>
      </div>
      {formError && <div className="ts-alert ts-alert--error" role="alert">{formError}</div>}
      <div className="ts-actions">
        <button type="submit" className="btn btn--primary" disabled={saving}>{saving ? "Saving…" : editingId ? "Save changes" : "Add booking"}</button>
        <button type="button" className="ts-btn-secondary" onClick={onCancel} disabled={saving}>Cancel</button>
      </div>
    </form>
  );
}

export default function Bookings() {
  const [params, setParams] = useSearchParams();
  const tripFilter = params.get("trip") || "";
  const [state, setState] = useState({ status: "loading", trips: [], bookings: [], error: "" });
  const [reloadKey, setReloadKey] = useState(0);
  const [formState, setFormState] = useState(null);   // null | {initial, editingId}
  const [actionError, setActionError] = useState("");
  const [deleting, setDeleting] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([getTrips(), listBookings()])
      .then(([t, b]) => active && setState({ status: "ready", trips: t.trips || [], bookings: b.bookings || [], error: "" }))
      .catch((err) => active && setState({ status: "error", trips: [], bookings: [], error: err.message }));
    return () => { active = false; };
  }, [reloadKey]);

  const tripName = useMemo(() => Object.fromEntries(state.trips.map((t) => [t.id, t.destination])), [state.trips]);
  const visible = tripFilter ? state.bookings.filter((b) => b.trip_id === tripFilter) : state.bookings;
  const total = visible.reduce((sum, b) => sum + (b.amount_inr || 0), 0);

  function openAdd() {
    setFormState({ initial: { ...EMPTY, trip_id: state.trips.some((t) => t.id === tripFilter) ? tripFilter : "" }, editingId: null });
  }
  function openEdit(b) {
    setFormState({ editingId: b.id, initial: { trip_id: b.trip_id, kind: b.kind, title: b.title, provider: b.provider, reference: b.reference, start_date: b.start_date || "", end_date: b.end_date || "", amount: b.amount_inr != null ? String(Math.round(b.amount_inr)) : "", notes: b.notes } });
  }
  function handleSaved(booking) {
    setState((s) => ({ ...s, bookings: s.bookings.some((b) => b.id === booking.id) ? s.bookings.map((b) => (b.id === booking.id ? booking : b)) : [booking, ...s.bookings] }));
    setFormState(null);
  }
  async function handleDelete(b) {
    if (deleting || !window.confirm(`Delete "${b.title}"? This only removes it from TravelSync.`)) return;
    setDeleting(b.id); setActionError("");
    try { await deleteBooking(b.id); setState((s) => ({ ...s, bookings: s.bookings.filter((x) => x.id !== b.id) })); }
    catch (err) { setActionError(err.message); }
    finally { setDeleting(""); }
  }

  return (
    <main className="dashboard__content">
      <div className="ts-page-head">
        <span className="dashboard__eyebrow">BOOKINGS &amp; TICKETS</span>
        <h1>Your bookings</h1>
        <p>Keep hotel, flight, train, bus and activity details for each trip in one place. These are records you enter yourself — TravelSync doesn't make or confirm bookings.</p>
      </div>

      {state.status === "loading" && <div className="ts-empty" role="status">Loading your bookings…</div>}
      {state.status === "error" && (
        <div className="ts-alert ts-alert--error" role="alert">{state.error} <button type="button" className="notif__link" onClick={() => { setState({ status: "loading", trips: [], bookings: [], error: "" }); setReloadKey((k) => k + 1); }}>Try again</button></div>
      )}

      {state.status === "ready" && state.trips.length === 0 && (
        <div className="ts-empty"><h3>Create a trip first</h3><p>Bookings are attached to a trip.</p><Link className="btn btn--primary" to="/home">Plan a trip</Link></div>
      )}

      {state.status === "ready" && state.trips.length > 0 && (
        <>
          <div className="bookings-toolbar">
            <div className="ts-field">
              <label htmlFor="bk-filter">Show</label>
              <select id="bk-filter" value={tripFilter} onChange={(e) => (e.target.value ? setParams({ trip: e.target.value }) : setParams({}))}>
                <option value="">All trips</option>
                {state.trips.map((t) => <option key={t.id} value={t.id}>{t.destination}</option>)}
              </select>
            </div>
            {!formState && <button type="button" className="btn btn--primary" onClick={openAdd}><Plus size={16} /> Add booking</button>}
          </div>

          {actionError && <div className="ts-alert ts-alert--error" role="alert">{actionError}</div>}
          {formState && <BookingForm key={formState.editingId || "new"} trips={state.trips} initial={formState.initial} editingId={formState.editingId} onSaved={handleSaved} onCancel={() => setFormState(null)} />}

          {visible.length === 0 ? (
            <div className="ts-empty"><Ticket size={26} /><h3>No bookings yet</h3><p>Add your first booking to keep its details handy.</p></div>
          ) : (
            <>
              <ul className="ts-grid bookings-grid">
                {visible.map((b) => {
                  const Icon = (KIND[b.kind] || KIND.other).icon;
                  return (
                    <li key={b.id} className="booking-card">
                      <div className="booking-card__head"><span className="booking-card__icon"><Icon size={18} aria-hidden="true" /></span><div><strong>{b.title}</strong><span className="ts-muted ts-small">{(KIND[b.kind] || KIND.other).label} · {tripName[b.trip_id] || "Trip"}</span></div></div>
                      {b.provider && <span className="ts-muted">{b.provider}</span>}
                      {(b.start_date || b.end_date) && <span>{formatDate(b.start_date)}{b.end_date && b.end_date !== b.start_date ? ` → ${formatDate(b.end_date)}` : ""}</span>}
                      {b.reference && <span>Ref: <code>{b.reference}</code></span>}
                      {b.amount_inr != null && <span className="ts-chip ts-chip--aqua">₹{Number(b.amount_inr).toLocaleString("en-IN")}</span>}
                      {b.notes && <p className="ts-muted">{b.notes}</p>}
                      <div className="ts-actions">
                        <button type="button" className="ts-btn-secondary" onClick={() => openEdit(b)} aria-label={`Edit ${b.title}`}><Pencil size={14} aria-hidden="true" /> Edit</button>
                        <button type="button" className="ts-btn-secondary ts-btn-danger" onClick={() => handleDelete(b)} disabled={deleting === b.id} aria-label={`Delete ${b.title}`}><Trash2 size={14} aria-hidden="true" /></button>
                      </div>
                    </li>
                  );
                })}
              </ul>
              {total > 0 && <p className="ts-muted bookings-total">Total recorded: <strong>₹{total.toLocaleString("en-IN")}</strong></p>}
            </>
          )}
        </>
      )}
    </main>
  );
}
