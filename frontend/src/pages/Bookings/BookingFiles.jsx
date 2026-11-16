import { useRef, useState } from "react";
import { Download, ExternalLink, FileText, Paperclip, Trash2 } from "lucide-react";
import { ACCEPTED_FILE_TYPES, MAX_FILES_PER_BOOKING, bookingFileUrl } from "../../services/bookingApi";
import { checkFiles, fileSize, uploadAll } from "../../utils/bookingFiles";

// The files attached to one booking: open, download, remove (asks first) and attach more.
// Only people who may change the booking (`booking.can_edit`) see Remove and Attach.
export default function BookingFiles({ booking, onChange, onError, onAskRemove }) {
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);
  const files = booking.attachments;

  async function handlePick(e) {
    const picked = [...e.target.files];
    e.target.value = "";
    if (!picked.length) return;
    const problem = checkFiles(picked, files.length);
    if (problem) { onError(problem); return; }
    setBusy(true); onError("");
    const { attachments, failures } = await uploadAll(booking.id, picked);
    if (attachments.length) onChange({ ...booking, attachments: [...files, ...attachments] });
    if (failures.length) onError(failures.join("; "));
    setBusy(false);
  }

  return (
    <div className="booking-files">
      {files.length === 0 && <p className="ts-muted">No tickets or documents attached yet.</p>}
      {files.length > 0 && (
        <ul aria-label="Attached files">
          {files.map((f) => (
            <li key={f.id}>
              <FileText size={18} aria-hidden="true" />
              <span className="booking-files__name">{f.filename}<small className="ts-muted">{fileSize(f.size)}</small></span>
              <a className="booking-files__btn" href={bookingFileUrl(booking.id, f.id)} target="_blank" rel="noreferrer" aria-label={`Open ${f.filename}`} title="Open"><ExternalLink size={16} aria-hidden="true" /></a>
              <a className="booking-files__btn" href={bookingFileUrl(booking.id, f.id, true)} aria-label={`Download ${f.filename}`} title="Download"><Download size={16} aria-hidden="true" /></a>
              {booking.can_edit && <button type="button" className="booking-files__btn" onClick={() => onAskRemove(f)} aria-label={`Remove ${f.filename}`} title="Remove"><Trash2 size={16} aria-hidden="true" /></button>}
            </li>
          ))}
        </ul>
      )}
      {booking.can_edit && files.length < MAX_FILES_PER_BOOKING && (
        <>
          <input ref={inputRef} type="file" multiple accept={ACCEPTED_FILE_TYPES} onChange={handlePick} hidden aria-label={`Attach files to ${booking.title}`} />
          <button type="button" className="ts-btn-secondary booking-files__attach" onClick={() => inputRef.current?.click()} disabled={busy}>
            <Paperclip size={14} aria-hidden="true" /> {busy ? "Uploading…" : "Attach ticket / PDF"}
          </button>
        </>
      )}
    </div>
  );
}
