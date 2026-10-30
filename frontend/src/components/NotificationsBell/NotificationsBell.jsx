import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { listNotifications, markAllRead, markRead } from "../../services/notificationApi";
import { isAbort } from "../../services/apiClient";
import "./NotificationsBell.css";

const POLL_MS = 60_000;

function timeAgo(iso) {
  if (!iso) return "";
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short" }).format(new Date(iso));
}

// In-app notifications created by real events (someone joined your group, suggested a destination, a destination was
// chosen). It checks for new ones every minute while the page is open; there are no push or email notifications.
export default function NotificationsBell() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const rootRef = useRef(null);
  const buttonRef = useRef(null);
  const panelId = useId();

  const applyResult = useCallback((data) => {
    setItems(data.notifications || []);
    setUnread(data.unread_count || 0);
    setError("");
    setLoaded(true);
  }, []);
  const applyError = useCallback((err) => {
    if (!isAbort(err)) { setError(err.message); setLoaded(true); }
  }, []);

  // Check on mount and then once a minute while the tab is visible. State is only set in promise callbacks.
  useEffect(() => {
    const controller = new AbortController();
    const check = (signal) => listNotifications(signal).then(applyResult).catch(applyError);
    check(controller.signal);
    const timer = setInterval(() => { if (document.visibilityState === "visible") check(); }, POLL_MS);
    return () => { controller.abort(); clearInterval(timer); };
  }, [applyResult, applyError]);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (e) => { if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false); };
    const onKeyDown = (e) => { if (e.key === "Escape") { setOpen(false); buttonRef.current?.focus(); } };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => { document.removeEventListener("pointerdown", onPointerDown); document.removeEventListener("keydown", onKeyDown); };
  }, [open]);

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next) listNotifications().then(applyResult).catch(applyError);
  }

  async function openItem(item) {
    setOpen(false);
    if (!item.read) {
      try { await markRead(item.id); setItems((prev) => prev.map((n) => (n.id === item.id ? { ...n, read: true } : n))); setUnread((n) => Math.max(0, n - 1)); } catch { /* the link still works */ }
    }
    if (item.link) navigate(item.link);
  }

  async function readAll() {
    try { await markAllRead(); setItems((prev) => prev.map((n) => ({ ...n, read: true }))); setUnread(0); }
    catch (err) { setError(err.message); }
  }

  return (
    <div className="notif" ref={rootRef}>
      <button type="button" ref={buttonRef} className="dashboard__icon-btn" onClick={toggle} aria-haspopup="true" aria-expanded={open}
        aria-controls={open ? panelId : undefined} aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}>
        <Bell size={19} aria-hidden="true" />
        {unread > 0 && <span className="notif__badge" aria-hidden="true">{unread > 9 ? "9+" : unread}</span>}
      </button>

      {open && (
        <div className="notif__panel" id={panelId} role="region" aria-label="Notifications">
          <div className="notif__header">
            <strong>Notifications</strong>
            {unread > 0 && <button type="button" className="notif__link" onClick={readAll}>Mark all read</button>}
          </div>
          {error && <p className="notif__empty notif__empty--error" role="alert">{error}</p>}
          {!error && !loaded && <p className="notif__empty">Loading…</p>}
          {!error && loaded && items.length === 0 && <p className="notif__empty">You're all caught up. Group activity will show up here.</p>}
          <ul>
            {items.map((item) => (
              <li key={item.id}>
                <button type="button" className={`notif__item${item.read ? "" : " is-unread"}`} onClick={() => openItem(item)}>
                  <span>{item.message}</span>
                  <small>{timeAgo(item.created_at)}</small>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
