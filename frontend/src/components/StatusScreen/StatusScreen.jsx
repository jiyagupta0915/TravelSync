import { AlertTriangle } from "lucide-react";
import "./StatusScreen.css";

// Full-page loading / error state used while the session is being checked.
export default function StatusScreen({ kind = "loading", title, message, onRetry }) {
  if (kind === "loading") {
    return (
      <div className="status-screen" role="status" aria-live="polite">
        <span className="status-screen__spinner" aria-hidden="true" />
        <p>{message || "Loading…"}</p>
      </div>
    );
  }
  return (
    <div className="status-screen" role="alert">
      <div className="status-screen__icon"><AlertTriangle size={24} /></div>
      <h1>{title}</h1>
      {message && <p>{message}</p>}
      {onRetry && <button type="button" className="btn btn--primary" onClick={onRetry}>Try again</button>}
    </div>
  );
}
