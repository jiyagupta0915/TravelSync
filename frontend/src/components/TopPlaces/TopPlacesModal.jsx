import { useEffect } from "react";
import { ArrowRight, X } from "lucide-react";
import TopPlaces from "./TopPlaces";
import "./TopPlaces.css";

// onChoose is optional: leave it out (e.g. for already-saved trips) and the modal just shows a Close button.
export default function TopPlacesModal({ destination, onClose, onChoose, choosing = false, closeLabel = onChoose ? "Back to matches" : "Close" }) {
  useEffect(() => {
    if (!destination) return undefined;
    const onKeyDown = (event) => { if (event.key === "Escape") onClose(); };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [destination, onClose]);

  if (!destination) return null;

  return (
    <div className="places-modal" onClick={onClose}>
      <div
        className="places-modal__panel"
        role="dialog"
        aria-modal="true"
        aria-label={`Top places in ${destination}`}
        onClick={(event) => event.stopPropagation()}
      >
        <button type="button" className="places-modal__close" onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>
        <div className="places-modal__scroll">
          <TopPlaces destination={destination} />
        </div>
        <div className="places-modal__footer">
          <button type="button" className={onChoose ? "places-modal__secondary" : "places-modal__primary"} onClick={onClose}>{closeLabel}</button>
          {onChoose && (
            <button type="button" className="places-modal__primary" onClick={onChoose} disabled={choosing}>
              {choosing ? "Saving…" : `Choose ${destination}`} <ArrowRight size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
