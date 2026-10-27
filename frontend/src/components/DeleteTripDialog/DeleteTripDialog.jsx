import { useEffect, useRef, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { deleteTrip } from "../../services/tripHubApi";
import "./DeleteTripDialog.css";

// Asks "are you sure?" before permanently deleting a trip.
// Render it only while a trip is selected, with key={trip.id}, so its state starts fresh each time.
export default function DeleteTripDialog({ trip, onClose, onDeleted }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const cancelRef = useRef(null);

  useEffect(() => {
    cancelRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previousOverflow; };
  }, []);

  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === "Escape" && !busy) onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, onClose]);

  async function confirmDelete() {
    setBusy(true);
    setError("");
    try {
      await deleteTrip(trip.id);
      onDeleted(trip);
    } catch (err) {
      if (err.status === 404) {   // already deleted somewhere else: treat it as done
        onDeleted(trip);
        return;
      }
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="delete-dialog" onClick={() => !busy && onClose()}>
      <div
        className="delete-dialog__panel"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-text"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="delete-dialog__icon"><AlertTriangle size={22} /></div>
        <h3 id="delete-dialog-title">Delete your trip to {trip.destination}?</h3>
        <p id="delete-dialog-text">
          This permanently removes the trip, its packing list and the stays you shortlisted. This can't be undone.
        </p>
        {error && <p className="delete-dialog__error" role="alert">{error}</p>}
        <div className="delete-dialog__actions">
          <button type="button" ref={cancelRef} className="delete-dialog__cancel" onClick={onClose} disabled={busy}>
            Keep trip
          </button>
          <button type="button" className="delete-dialog__confirm" onClick={confirmDelete} disabled={busy}>
            {busy ? "Deleting…" : "Yes, delete trip"}
          </button>
        </div>
      </div>
    </div>
  );
}