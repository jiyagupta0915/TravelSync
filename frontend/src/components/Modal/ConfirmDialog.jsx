import { Trash2 } from "lucide-react";
import Modal from "./Modal";

// "Are you sure?" box for destructive actions. Cancel is focused first, so Enter never deletes by accident.
export default function ConfirmDialog({ title, children, confirmLabel = "Delete", busy = false, error = "", onConfirm, onCancel }) {
  return (
    <Modal title={title} icon={<Trash2 size={20} />} size="sm" layer="top" busy={busy} onClose={onCancel}>
      <div className="modal__text">{children}</div>
      {error && <div className="ts-alert ts-alert--error" role="alert">{error}</div>}
      <div className="modal__actions">
        <button type="button" className="ts-btn-secondary" onClick={onCancel} disabled={busy} autoFocus>Cancel</button>
        <button type="button" className="modal__danger" onClick={onConfirm} disabled={busy}>{busy ? "Deleting…" : confirmLabel}</button>
      </div>
    </Modal>
  );
}
