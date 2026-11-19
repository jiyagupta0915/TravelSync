import { useEffect, useState } from "react";
import { Pencil } from "lucide-react";
import NumberField from "../NumberField/NumberField";
import { updateTrip } from "../../services/tripApi";
import { parsePositiveInteger } from "../../utils/numberField";
import { MAX_BUDGET_INR, MAX_DURATION_DAYS, MIN_DURATION_DAYS } from "../../utils/limits";
import { daysBetween } from "../../pages/Trips/tripFormat";
import "../../styles/appPages.css";
import "./EditTripDialog.css";

// Edit budget, days and (optional) dates of a saved trip.
// Render only while a trip is selected, with key={trip.id}, so its state starts fresh each time.
export default function EditTripDialog({ trip, onClose, onSaved }) {
  const [budget, setBudget] = useState(trip.budget ? String(Math.round(trip.budget)) : "");
  const [duration, setDuration] = useState(trip.duration ? String(trip.duration) : "");
  const [start, setStart] = useState(trip.start_date || "");
  const [end, setEnd] = useState(trip.end_date || "");
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);

  const hasDates = Boolean(start && end);
  const derivedDays = hasDates && end >= start ? daysBetween(start, end) : null;

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previousOverflow; };
  }, []);

  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === "Escape" && !busy) onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, onClose]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (busy) return;
    const next = {};
    const payload = {};

    if (budget !== "") {
      const parsed = parsePositiveInteger(budget, { label: "your budget", max: MAX_BUDGET_INR });
      if (parsed.ok) payload.budget = parsed.value; else next.budget = parsed.error;
    }

    if (Boolean(start) !== Boolean(end)) {
      next.dates = "Add both a start and an end date, or leave both empty.";
    } else if (hasDates) {
      if (end < start) next.dates = "The end date can't be earlier than the start date.";
      else if (daysBetween(start, end) > MAX_DURATION_DAYS) next.dates = `A trip can be at most ${MAX_DURATION_DAYS} days long.`;
      else { payload.start_date = start; payload.end_date = end; }
    } else {
      payload.start_date = null;   // no dates: make sure any old dates are cleared
      payload.end_date = null;
      if (duration !== "") {
        const parsed = parsePositiveInteger(duration, { label: "the number of days", min: MIN_DURATION_DAYS, max: MAX_DURATION_DAYS });
        if (parsed.ok) payload.duration = parsed.value; else next.duration = parsed.error;
      }
    }

    setErrors(next);
    if (Object.keys(next).length) return;

    setBusy(true);
    try {
      const { trip: updated } = await updateTrip(trip.id, payload);
      onSaved(updated);
    } catch (err) {
      setErrors({ form: err.message });
      setBusy(false);
    }
  }

  return (
    <div className="edit-dialog" onClick={() => !busy && onClose()}>
      <form
        className="edit-dialog__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-dialog-title"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
        noValidate
      >
        <div className="edit-dialog__icon"><Pencil size={20} /></div>
        <h3 id="edit-dialog-title">Edit your trip to {trip.destination}</h3>

        <div className="ts-form">
          <div className="ts-field">
            <label htmlFor="edit-budget">Total budget</label>
            <div className="ts-input-unit">
              <b>₹</b>
              <NumberField id="edit-budget" value={budget} maxLength={8} onChange={(v) => { setBudget(v); setErrors((e) => ({ ...e, budget: undefined })); }} invalid={Boolean(errors.budget)} />
            </div>
            <small className="edit-dialog__hint">What you plan to spend on the whole trip: stay, food, travel and activities.</small>
            {errors.budget && <span className="ts-error" role="alert">{errors.budget}</span>}
          </div>

          <div className="ts-field">
            <label htmlFor="edit-days">Number of days</label>
            <input
              id="edit-days"
              type="number"
              min={MIN_DURATION_DAYS}
              max={MAX_DURATION_DAYS}
              value={hasDates ? (derivedDays ?? "") : duration}
              readOnly={hasDates}
              onChange={(e) => { setDuration(e.target.value); setErrors((er) => ({ ...er, duration: undefined })); }}
              aria-invalid={Boolean(errors.duration) || undefined}
            />
            <small className="edit-dialog__hint">
              {hasDates ? "Worked out from your dates." : "How many days you'll be away."}
            </small>
            {errors.duration && <span className="ts-error" role="alert">{errors.duration}</span>}
          </div>

          <div className="ts-field">
            <label>Travel dates <span className="ts-hint">(optional)</span></label>
            <div className="edit-dialog__dates">
              <input type="date" aria-label="Trip start date" value={start} onChange={(e) => { setStart(e.target.value); setErrors((er) => ({ ...er, dates: undefined })); }} />
              <input type="date" aria-label="Trip end date" value={end} min={start || undefined} onChange={(e) => { setEnd(e.target.value); setErrors((er) => ({ ...er, dates: undefined })); }} />
            </div>
            <small className="edit-dialog__hint">
              Not decided yet? Leave these empty. Adding them gives you a real weather forecast and fills in your bookings.
            </small>
            {(start || end) && (
              <button type="button" className="edit-dialog__clear" onClick={() => { setStart(""); setEnd(""); }}>Clear dates</button>
            )}
            {errors.dates && <span className="ts-error" role="alert">{errors.dates}</span>}
          </div>
        </div>

        {errors.form && <p className="edit-dialog__error" role="alert">{errors.form}</p>}

        <div className="edit-dialog__actions">
          <button type="button" className="edit-dialog__cancel" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? "Saving…" : "Save changes"}</button>
        </div>
      </form>
    </div>
  );
}