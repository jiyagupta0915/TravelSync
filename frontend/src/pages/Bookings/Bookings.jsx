import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ChevronRight, ExternalLink, FileText, Pencil, Plus, Ticket, Trash2, Users } from "lucide-react";
import Modal from "../../components/Modal/Modal";
import ConfirmDialog from "../../components/Modal/ConfirmDialog";
import { getTrips } from "../../services/tripApi";
import { listGroups } from "../../services/groupApi";
import { bookingFileUrl, deleteBooking, deleteBookingFile, listBookings, shareBookingToChat } from "../../services/bookingApi";
import { normalizeBooking } from "../../utils/bookingFiles";
import BookingDetails from "./BookingDetails";
import BookingForm from "./BookingForm";
import { EMPTY_BOOKING, formatRange, kindOf } from "./bookingKinds";
import "../../styles/appPages.css";
import "./Bookings.css";

export default function Bookings() {
  const [params, setParams] = useSearchParams();
  const filter = params.get("group") ? `group:${params.get("group")}` : params.get("trip") ? `trip:${params.get("trip")}` : "";
  const [state, setState] = useState({ status: "loading", trips: [], groups: [], bookings: [], error: "" });
  const [reloadKey, setReloadKey] = useState(0);
  const [modal, setModal] = useState(null);       // null | { mode: "add", initial } | { mode: "view" | "edit", id }
  const [confirm, setConfirm] = useState(null);   // null | { booking } (delete booking) | { booking, file } (remove file)
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [confirmError, setConfirmError] = useState("");
  const [actionError, setActionError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([getTrips(), listGroups(), listBookings()])
      .then(([t, g, b]) => active && setState({ status: "ready", trips: t.trips || [], groups: g.groups || [], bookings: (b.bookings || []).map(normalizeBooking), error: "" }))
      .catch((err) => active && setState({ status: "error", trips: [], groups: [], bookings: [], error: err.message }));
    return () => { active = false; };
  }, [reloadKey]);

  const tripName = useMemo(() => Object.fromEntries(state.trips.map((t) => [t.id, t.destination])), [state.trips]);
  const whereOf = (b) => (b.scope === "group" ? b.group_name || "Group" : tripName[b.trip_id] || "Trip");
  const visible = state.bookings.filter((b) => {
    if (filter.startsWith("trip:")) return b.trip_id === filter.slice(5);
    if (filter.startsWith("group:")) return b.group_id === filter.slice(6);
    return true;
  });
  const total = visible.reduce((sum, b) => sum + (b.amount_inr || 0), 0);
  const nothingToAttachTo = state.trips.length === 0 && state.groups.length === 0;
  const open = modal && modal.mode !== "add" ? state.bookings.find((b) => b.id === modal.id) : null;

  const replaceBooking = (booking) => setState((s) => ({ ...s, bookings: s.bookings.map((b) => (b.id === booking.id ? { ...b, ...booking } : b)) }));
  const closeModal = () => { setModal(null); setActionError(""); };

  function openAdd() {
    const initial = { ...EMPTY_BOOKING };
    if (filter.startsWith("group:") && state.groups.some((g) => g.id === filter.slice(6))) { initial.scope = "group"; initial.group_id = filter.slice(6); }
    else if (filter.startsWith("trip:") && state.trips.some((t) => t.id === filter.slice(5))) initial.trip_id = filter.slice(5);
    else if (state.trips.length === 0) initial.scope = "group";
    setNotice(""); setActionError(""); setModal({ mode: "add", initial });
  }
  const openView = (id) => { setNotice(""); setActionError(""); setModal({ mode: "view", id }); };

  function editInitial(b) {
    return { scope: b.scope === "group" ? "group" : "trip", trip_id: b.trip_id || "", group_id: b.group_id || "", share_to_chat: false, kind: b.kind, title: b.title, provider: b.provider, reference: b.reference, start_date: b.start_date || "", end_date: b.end_date || "", amount: b.amount_inr != null ? String(Math.round(b.amount_inr)) : "", notes: b.notes };
  }

  function handleSaved(saved, warning = "") {
    setState((s) => ({ ...s, bookings: s.bookings.some((b) => b.id === saved.id) ? s.bookings.map((b) => (b.id === saved.id ? saved : b)) : [saved, ...s.bookings] }));
    setNotice(warning);
    setModal(modal.mode === "edit" ? { mode: "view", id: saved.id } : null);
  }

  async function handleShare(b) {
    setActionError(""); setNotice("");
    try { await shareBookingToChat(b.id); setNotice(`"${b.title}" was posted in the ${b.group_name} chat.`); setModal(null); }
    catch (err) { setActionError(err.message); }
  }

  async function handleConfirm() {
    setConfirmBusy(true); setConfirmError("");
    try {
      if (confirm.file) {
        await deleteBookingFile(confirm.booking.id, confirm.file.id);
        replaceBooking({ ...confirm.booking, attachments: confirm.booking.attachments.filter((a) => a.id !== confirm.file.id) });
      } else {
        await deleteBooking(confirm.booking.id);
        setState((s) => ({ ...s, bookings: s.bookings.filter((x) => x.id !== confirm.booking.id) }));
        if (modal && modal.id === confirm.booking.id) setModal(null);
      }
      setConfirm(null);
    } catch (err) {
      setConfirmError(err.message);
    } finally {
      setConfirmBusy(false);
    }
  }
  const askDelete = (booking) => { setConfirmError(""); setConfirm({ booking }); };
  const askRemoveFile = (booking, file) => { setConfirmError(""); setConfirm({ booking, file }); };

  return (
    <main className="dashboard__content">
      <div className="ts-page-head">
        <span className="dashboard__eyebrow">BOOKINGS &amp; TICKETS</span>
        <h1>Your bookings</h1>
        <p>Keep hotel, flight, train, bus and activity details, and the ticket PDFs, for each trip in one place. Keep them private, or share them with a travel group. These are records you enter yourself; TravelSync doesn't make or confirm bookings.</p>
      </div>

      {state.status === "loading" && <div className="ts-empty" role="status">Loading your bookings…</div>}
      {state.status === "error" && (
        <div className="ts-alert ts-alert--error" role="alert">{state.error} <button type="button" className="notif__link" onClick={() => { setState({ status: "loading", trips: [], groups: [], bookings: [], error: "" }); setReloadKey((k) => k + 1); }}>Try again</button></div>
      )}

      {state.status === "ready" && nothingToAttachTo && (
        <div className="ts-empty"><h3>Create a trip or join a group first</h3><p>Bookings are attached to one of your trips or to a travel group.</p><Link className="btn btn--primary" to="/home">Plan a trip</Link></div>
      )}

      {state.status === "ready" && !nothingToAttachTo && (
        <>
          <div className="bookings-toolbar">
            <div className="ts-field">
              <label htmlFor="bk-filter">Show</label>
              <select id="bk-filter" value={filter} onChange={(e) => {
                const v = e.target.value;
                if (!v) setParams({}); else if (v.startsWith("group:")) setParams({ group: v.slice(6) }); else setParams({ trip: v.slice(5) });
              }}>
                <option value="">Everything</option>
                {state.trips.length > 0 && <optgroup label="My trips">{state.trips.map((t) => <option key={t.id} value={`trip:${t.id}`}>{t.destination}</option>)}</optgroup>}
                {state.groups.length > 0 && <optgroup label="Groups">{state.groups.map((g) => <option key={g.id} value={`group:${g.id}`}>{g.name}</option>)}</optgroup>}
              </select>
            </div>
            <button type="button" className="btn btn--primary" onClick={openAdd}><Plus size={16} aria-hidden="true" /> Add booking</button>
          </div>

          {!modal && actionError && <div className="ts-alert ts-alert--error" role="alert">{actionError}</div>}
          {notice && <div className="ts-alert ts-alert--info" role="status">{notice}</div>}

          {visible.length === 0 ? (
            <div className="ts-empty"><Ticket size={26} aria-hidden="true" /><h3>No bookings yet</h3><p>Add your first booking to keep its details and tickets handy.</p></div>
          ) : (
            <>
              <ul className="ts-grid bookings-grid">
                {visible.map((b) => {
                  const kind = kindOf(b.kind);
                  const Icon = kind.icon;
                  const dates = formatRange(b.start_date, b.end_date);
                  return (
                    <li key={b.id} className="booking-card" onClick={() => openView(b.id)}>
                      <div className="booking-card__head">
                        <span className="booking-card__icon"><Icon size={18} aria-hidden="true" /></span>
                        <div className="booking-card__titles">
                          <button type="button" className="booking-card__title" onClick={(e) => { e.stopPropagation(); openView(b.id); }} aria-label={`View details of ${b.title}`}>{b.title}</button>
                          <span className="ts-muted ts-small">{kind.label} · {whereOf(b)}</span>
                        </div>
                        {b.can_edit && (
                          <button type="button" className="booking-card__delete" onClick={(e) => { e.stopPropagation(); askDelete(b); }} aria-label={`Delete ${b.title}`} title="Delete"><Trash2 size={16} aria-hidden="true" /></button>
                        )}
                      </div>
                      {b.scope === "group" && <span className="ts-chip ts-chip--peach booking-card__scope"><Users size={12} aria-hidden="true" /> Shared{b.created_by ? ` · added by ${b.created_by}` : ""}</span>}
                      {dates && <span className="booking-card__dates">{dates}</span>}
                      {b.amount_inr != null && <span className="ts-chip ts-chip--aqua booking-card__amount">₹{Number(b.amount_inr).toLocaleString("en-IN")}</span>}
                      {b.attachments.length > 0 && (
                        <ul className="booking-card__files" aria-label={`Files attached to ${b.title}`}>
                          {b.attachments.map((f) => (
                            <li key={f.id}>
                              <a href={bookingFileUrl(b.id, f.id)} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} title={`Open ${f.filename}`} aria-label={`Open ${f.filename}`}>
                                <FileText size={14} aria-hidden="true" /><span>{f.filename}</span><ExternalLink size={12} aria-hidden="true" />
                              </a>
                            </li>
                          ))}
                        </ul>
                      )}
                      <span className="booking-card__more">View details <ChevronRight size={14} aria-hidden="true" /></span>
                    </li>
                  );
                })}
              </ul>
              {total > 0 && <p className="ts-muted bookings-total">Total recorded: <strong>₹{total.toLocaleString("en-IN")}</strong></p>}
            </>
          )}
        </>
      )}

      {modal?.mode === "add" && (
        <Modal title="Add a booking" icon={<Plus size={20} />} size="lg" onClose={closeModal}>
          <BookingForm trips={state.trips} groups={state.groups} initial={modal.initial} editingId={null} onSaved={handleSaved} onCancel={closeModal} />
        </Modal>
      )}
      {open && modal.mode === "edit" && (
        <Modal title="Edit booking" icon={<Pencil size={20} />} size="lg" onClose={() => setModal({ mode: "view", id: open.id })}>
          <BookingForm key={open.id} trips={state.trips} groups={state.groups} initial={editInitial(open)} editingId={open.id} onSaved={handleSaved} onCancel={() => setModal({ mode: "view", id: open.id })} />
        </Modal>
      )}
      {open && modal.mode === "view" && (
        <BookingDetails
          booking={open} where={whereOf(open)} error={actionError}
          onClose={closeModal} onEdit={() => { setActionError(""); setModal({ mode: "edit", id: open.id }); }}
          onDelete={() => askDelete(open)} onShare={() => handleShare(open)}
          onFilesChange={replaceBooking} onError={setActionError} onAskRemoveFile={(file) => askRemoveFile(open, file)}
        />
      )}
      {confirm && (
        <ConfirmDialog
          title={confirm.file ? "Remove this file?" : "Delete this booking?"}
          confirmLabel={confirm.file ? "Remove file" : "Delete booking"}
          busy={confirmBusy} error={confirmError} onConfirm={handleConfirm} onCancel={() => setConfirm(null)}
        >
          {confirm.file ? (
            <p><b>{confirm.file.filename}</b> will be removed from "{confirm.booking.title}".</p>
          ) : (
            <>
              <p><b>{confirm.booking.title}</b> and all the files attached to it will be deleted.{confirm.booking.scope === "group" ? " It will disappear for everyone in the group." : ""}</p>
              <p>This only removes it from TravelSync. Your real booking is not cancelled.</p>
            </>
          )}
        </ConfirmDialog>
      )}
    </main>
  );
}
