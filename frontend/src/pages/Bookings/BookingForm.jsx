import { useState } from "react";
import { Users, User, X } from "lucide-react";
import NumberField from "../../components/NumberField/NumberField";
import { ACCEPTED_FILE_TYPES, MAX_FILES_PER_BOOKING, MAX_FILE_MB, createBooking, updateBooking } from "../../services/bookingApi";
import { parsePositiveInteger } from "../../utils/numberField";
import { checkFiles, fileSize, normalizeBooking, uploadAll } from "../../utils/bookingFiles";
import { KINDS } from "./bookingKinds";

// Add (editingId = null) or edit a booking. Calls onSaved(booking, warning) when the server accepted it.
export default function BookingForm({ trips, groups, initial, editingId, onSaved, onCancel }) {
  const [form, setForm] = useState(initial);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [files, setFiles] = useState([]);
  const set = (key) => (e) => { setForm((f) => ({ ...f, [key]: e.target.value })); setErrors((er) => ({ ...er, [key]: undefined })); };

  function pickFiles(event) {
    const picked = [...event.target.files];
    event.target.value = "";                                   // so the same file can be picked again
    const all = [...files, ...picked];
    const problem = checkFiles(all);
    if (problem) { setErrors((er) => ({ ...er, files: problem })); return; }
    setFiles(all);
    setErrors((er) => ({ ...er, files: undefined }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (saving) return;
    const next = {};
    if (form.scope === "trip" && !form.trip_id) next.trip_id = "Choose which trip this belongs to.";
    if (form.scope === "group" && !form.group_id) next.group_id = "Choose which group this belongs to.";
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
      const target = form.scope === "group" ? { group_id: form.group_id, share_to_chat: form.share_to_chat } : { trip_id: form.trip_id };
      let { booking } = editingId ? await updateBooking(editingId, body) : await createBooking({ ...body, ...target });
      booking = normalizeBooking(booking);
      let warning = "";
      if (!editingId && files.length) {
        const { attachments, failures } = await uploadAll(booking.id, files);
        booking = { ...booking, attachments };
        if (failures.length) warning = `Booking saved, but some files weren't attached: ${failures.join("; ")}. You can add them again from the booking.`;
      }
      onSaved(booking, warning);
    } catch (err) {
      setFormError(err.message);
      setSaving(false);
    }
  }

  return (
    <form className="booking-form" onSubmit={handleSubmit} noValidate aria-label={editingId ? "Edit booking" : "Add a booking"}>
      <p className="ts-muted">Record a reservation you made elsewhere. TravelSync keeps your details in one place; it doesn't book or confirm anything for you.</p>
      <div className="ts-form ts-form--wide">
        {!editingId && (
          <fieldset className="bookings-scope">
            <legend>Who is this booking for?</legend>
            <label className="bookings-scope__option">
              <input type="radio" name="bk-scope" checked={form.scope === "trip"} onChange={() => setForm((f) => ({ ...f, scope: "trip", share_to_chat: false }))} />
              <span><b><User size={14} aria-hidden="true" /> Just me</b><small>Saved on one of your trips. Only you can see it.</small></span>
            </label>
            <label className="bookings-scope__option">
              <input type="radio" name="bk-scope" checked={form.scope === "group"} disabled={groups.length === 0} onChange={() => setForm((f) => ({ ...f, scope: "group" }))} />
              <span><b><Users size={14} aria-hidden="true" /> A travel group</b><small>{groups.length === 0 ? "Join or create a group first." : "Everyone in the group can see it."}</small></span>
            </label>
          </fieldset>
        )}
        {form.scope === "trip" ? (
          <div className="ts-field">
            <label htmlFor="bk-trip">Trip</label>
            <select id="bk-trip" value={form.trip_id} onChange={set("trip_id")} disabled={Boolean(editingId)} aria-invalid={Boolean(errors.trip_id) || undefined}>
              <option value="">Select a trip…</option>
              {trips.map((t) => <option key={t.id} value={t.id}>{t.destination}{t.duration ? ` · ${t.duration} days` : ""}</option>)}
            </select>
            {errors.trip_id && <span className="ts-error" role="alert">{errors.trip_id}</span>}
          </div>
        ) : (
          <div className="ts-field">
            <label htmlFor="bk-group">Group</label>
            <select id="bk-group" value={form.group_id} onChange={set("group_id")} disabled={Boolean(editingId)} aria-invalid={Boolean(errors.group_id) || undefined}>
              <option value="">Select a group…</option>
              {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
            {errors.group_id && <span className="ts-error" role="alert">{errors.group_id}</span>}
          </div>
        )}
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
          <label htmlFor="bk-ref">Confirmation no. <span className="ts-hint">(optional)</span></label>
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
        <div className="ts-field bookings-wide">
          <label htmlFor="bk-notes">Notes <span className="ts-hint">(optional)</span></label>
          <textarea id="bk-notes" value={form.notes} maxLength={500} onChange={set("notes")} />
        </div>
        {!editingId && (
          <div className="ts-field bookings-wide bookings-filepick">
            <label htmlFor="bk-files">Tickets / documents <span className="ts-hint">(optional · PDF, PNG, JPEG or WebP · up to {MAX_FILE_MB} MB each, {MAX_FILES_PER_BOOKING} files)</span></label>
            <input id="bk-files" type="file" multiple accept={ACCEPTED_FILE_TYPES} onChange={pickFiles} aria-invalid={Boolean(errors.files) || undefined} />
            {errors.files && <span className="ts-error" role="alert">{errors.files}</span>}
            {files.length > 0 && (
              <ul className="bookings-chosen" aria-label="Files to attach">
                {files.map((f, i) => (
                  <li key={`${f.name}-${i}`}>
                    <span>{f.name}</span><span className="ts-muted ts-small">{fileSize(f.size)}</span>
                    <button type="button" onClick={() => setFiles((all) => all.filter((_, j) => j !== i))} aria-label={`Don't attach ${f.name}`}><X size={14} aria-hidden="true" /></button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {!editingId && form.scope === "group" && (
          <label className="bookings-check bookings-wide">
            <input type="checkbox" checked={form.share_to_chat} onChange={(e) => setForm((f) => ({ ...f, share_to_chat: e.target.checked }))} />
            <span>Also post this booking in the group chat <small>Title and dates only. Never the confirmation number, amount or files.</small></span>
          </label>
        )}
      </div>
      {formError && <div className="ts-alert ts-alert--error" role="alert">{formError}</div>}
      <div className="modal__actions">
        <button type="button" className="ts-btn-secondary" onClick={onCancel} disabled={saving}>Cancel</button>
        <button type="submit" className="btn btn--primary" disabled={saving}>{saving ? "Saving…" : editingId ? "Save changes" : "Add booking"}</button>
      </div>
    </form>
  );
}
