import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Users } from "lucide-react";
import { addSuggestion, listGroups } from "../../services/groupApi";
import "./ShareToGroupDialog.css";

const inr = (value) => `₹${Number(value).toLocaleString("en-IN")}`;

// Shares a destination found with "Find my destination" into one of the user's groups, together with the criteria
// they searched with (days, budget, interests), so the other members see why it was suggested and can vote on it.
// Render it only while a destination is selected, with key={destination}, so its state starts fresh each time.
// `criteria` = { duration, budget, preferences } as they were when the search ran.
export default function ShareToGroupDialog({ destination, state, criteria, onClose }) {
  const [groups, setGroups] = useState({ status: "loading", list: [], error: "" });
  const [groupId, setGroupId] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sharedWith, setSharedWith] = useState(null);
  const closeRef = useRef(null);

  useEffect(() => {
    closeRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previousOverflow; };
  }, []);

  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === "Escape" && !busy) onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, onClose]);

  useEffect(() => {
    let active = true;
    listGroups()
      .then((data) => {
        if (!active) return;
        const list = data.groups || [];
        setGroups({ status: "ready", list, error: "" });
        if (list.length === 1) setGroupId(list[0].id);
      })
      .catch((err) => active && setGroups({ status: "error", list: [], error: err.message }));
    return () => { active = false; };
  }, []);

  async function handleShare(event) {
    event.preventDefault();
    if (busy) return;
    if (!groupId) { setError("Choose which group to share with."); return; }
    setBusy(true);
    setError("");
    try {
      const payload = { destination, note: note.trim(), preferences: criteria.preferences || [] };
      if (criteria.duration) payload.duration = criteria.duration;
      if (criteria.budget) payload.budget = criteria.budget;
      await addSuggestion(groupId, payload);
      setSharedWith(groups.list.find((group) => group.id === groupId));
    } catch (err) {
      setError(err.message || "Could not share this destination.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="share-dialog" onClick={() => !busy && onClose()}>
      <div className="share-dialog__panel" role="dialog" aria-modal="true" aria-labelledby="share-dialog-title" onClick={(event) => event.stopPropagation()}>
        <div className="share-dialog__icon"><Users size={22} /></div>

        {sharedWith ? (
          <>
            <h3 id="share-dialog-title">Shared with {sharedWith.name}</h3>
            <p role="status"><Check size={14} aria-hidden="true" /> {destination} is now on the group's list. Members have been notified and can vote on it.</p>
            <div className="share-dialog__actions">
              <button type="button" ref={closeRef} className="share-dialog__cancel" onClick={onClose}>Done</button>
              <Link className="share-dialog__confirm" to={`/groups/${sharedWith.id}`}>Open group</Link>
            </div>
          </>
        ) : (
          <form onSubmit={handleShare} noValidate>
            <h3 id="share-dialog-title">Share {destination} with a group</h3>
            <p>Your group will see this destination with the trip details you searched with.</p>

            <div className="share-dialog__criteria" aria-label="Details that will be shared">
              {state && <span>{state}</span>}
              {criteria.duration && <span>{criteria.duration} days</span>}
              {criteria.budget && <span>{inr(criteria.budget)}</span>}
              {(criteria.preferences || []).map((preference) => <span key={preference} className="is-interest">{preference}</span>)}
            </div>

            {groups.status === "loading" && <p className="share-dialog__muted" role="status">Loading your groups…</p>}
            {groups.status === "error" && <p className="share-dialog__error" role="alert">{groups.error}</p>}
            {groups.status === "ready" && groups.list.length === 0 && (
              <p className="share-dialog__muted">You're not in a group yet. <Link to="/groups">Create or join a group</Link> first, then come back to share.</p>
            )}
            {groups.list.length > 0 && (
              <>
                <fieldset className="share-dialog__groups">
                  <legend>Share with</legend>
                  {groups.list.map((group) => (
                    <label key={group.id} className={groupId === group.id ? "is-selected" : ""}>
                      <input type="radio" name="share-group" value={group.id} checked={groupId === group.id} onChange={() => { setGroupId(group.id); setError(""); }} />
                      <span><strong>{group.name}</strong><small>{group.member_count} {group.member_count === 1 ? "member" : "members"}</small></span>
                    </label>
                  ))}
                </fieldset>
                <label className="share-dialog__note" htmlFor="share-note">Why this place? <small>(optional)</small></label>
                <textarea id="share-note" value={note} maxLength={300} onChange={(event) => setNote(event.target.value)} placeholder="Add a short message for your group" />
              </>
            )}

            {error && <p className="share-dialog__error" role="alert">{error}</p>}
            <div className="share-dialog__actions">
              <button type="button" ref={closeRef} className="share-dialog__cancel" onClick={onClose} disabled={busy}>Cancel</button>
              {groups.list.length > 0 && <button type="submit" className="share-dialog__confirm" disabled={busy}>{busy ? "Sharing…" : "Share with group"}</button>}
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
