import { MessageSquare, Pencil, Trash2, Users } from "lucide-react";
import Modal from "../../components/Modal/Modal";
import BookingFiles from "./BookingFiles";
import { formatRange, kindOf } from "./bookingKinds";

function Detail({ label, wide, children }) {
  if (!children) return null;
  return <div className={`booking-details__item${wide ? " is-wide" : ""}`}><dt>{label}</dt><dd>{children}</dd></div>;
}

// Everything about one booking, opened by clicking its card.
export default function BookingDetails({ booking: b, where, error, onClose, onEdit, onDelete, onShare, onFilesChange, onError, onAskRemoveFile }) {
  const kind = kindOf(b.kind);
  const Icon = kind.icon;
  return (
    <Modal title={b.title} icon={<Icon size={20} />} size="lg" onClose={onClose}>
      <div className="booking-details__chips">
        <span className="ts-chip">{kind.label}</span>
        {b.scope === "group" && <span className="ts-chip ts-chip--peach"><Users size={12} aria-hidden="true" /> Shared with {b.group_name || "group"}</span>}
        {b.amount_inr != null && <span className="ts-chip ts-chip--aqua">₹{Number(b.amount_inr).toLocaleString("en-IN")}</span>}
      </div>

      <dl className="booking-details">
        <Detail label={b.scope === "group" ? "Group" : "Trip"}>{where}</Detail>
        <Detail label="Provider">{b.provider}</Detail>
        <Detail label="Dates">{formatRange(b.start_date, b.end_date)}</Detail>
        <Detail label="Confirmation / ticket number">{b.reference && <code>{b.reference}</code>}</Detail>
        <Detail label="Added by">{b.scope === "group" ? b.created_by : ""}</Detail>
        <Detail label="Notes" wide>{b.notes}</Detail>
      </dl>

      <h3 className="booking-details__heading">Tickets &amp; documents</h3>
      <BookingFiles booking={b} onChange={onFilesChange} onError={onError} onAskRemove={onAskRemoveFile} />

      {b.scope === "group" && !b.can_edit && <p className="ts-muted booking-details__note">Only {b.created_by || "the person who added it"} or the group owner can change this booking.</p>}
      {error && <div className="ts-alert ts-alert--error" role="alert">{error}</div>}

      <div className="modal__actions booking-details__actions">
        {b.can_edit && <button type="button" className="ts-btn-secondary ts-btn-danger" onClick={onDelete}><Trash2 size={14} aria-hidden="true" /> Delete</button>}
        {b.scope === "group" && <button type="button" className="ts-btn-secondary" onClick={onShare}><MessageSquare size={14} aria-hidden="true" /> Post in chat</button>}
        {b.can_edit && <button type="button" className="btn btn--primary" onClick={onEdit}><Pencil size={14} aria-hidden="true" /> Edit</button>}
      </div>
    </Modal>
  );
}
