import { useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import "./Modal.css";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// A centred dialog over a dimmed page. Esc, the X button or a click outside close it (unless `busy`).
// Keyboard focus stays inside while it is open and returns to where it was when it closes.
// size: "sm" (confirmations) | "md" (default) | "lg". `layer="top"` sits above another open modal.
export default function Modal({ title, icon, onClose, busy = false, size = "md", layer, children }) {
  const panelRef = useRef(null);
  const titleId = useId();

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const panel = panelRef.current;
    if (panel && !panel.contains(document.activeElement)) panel.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      if (previouslyFocused instanceof HTMLElement && document.contains(previouslyFocused)) previouslyFocused.focus();
    };
  }, []);

  function handleKeyDown(event) {
    if (event.key === "Escape") {
      event.stopPropagation();
      if (!busy) onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const items = [...panelRef.current.querySelectorAll(FOCUSABLE)];
    if (items.length === 0) { event.preventDefault(); return; }
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement === panelRef.current)) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  return createPortal(
    <div className={`modal${layer === "top" ? " modal--top" : ""}`} onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
      <div ref={panelRef} className={`modal__panel modal__panel--${size}`} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} onKeyDown={handleKeyDown}>
        <div className="modal__head">
          {icon && <span className="modal__icon" aria-hidden="true">{icon}</span>}
          <h2 id={titleId} className="modal__title">{title}</h2>
          <button type="button" className="modal__close" onClick={onClose} disabled={busy} aria-label="Close"><X size={18} aria-hidden="true" /></button>
        </div>
        <div className="modal__body">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
