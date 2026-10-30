import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, Copy, Crown, Send, ThumbsUp, Trash2, Users } from "lucide-react";
import NumberField from "../../components/NumberField/NumberField";
import {
  addSuggestion, decide, deleteGroup, deleteSuggestion, getGroup, leaveGroup, listMessages, listSuggestions,
  removeVote, reopenVoting, sendMessage, vote,
} from "../../services/groupApi";
import { getFeatures, searchDestinations } from "../../services/recommendationApi";
import { createTrip } from "../../services/tripApi";
import { isAbort } from "../../services/apiClient";
import { MAX_BUDGET_INR, MAX_DURATION_DAYS } from "../../utils/limits";
import { parsePositiveInteger } from "../../utils/numberField";
import "../Packing/Packing.css";
import "../../styles/appPages.css";
import "./Groups.css";

const CHAT_POLL_MS = 4000;
const SUGGESTION_POLL_MS = 10000;

const inr = (value) => `₹${Number(value).toLocaleString("en-IN")}`;
const clock = (iso) => new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit", day: "numeric", month: "short" }).format(new Date(iso));

function Chat({ groupId }) {
  const [messages, setMessages] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const lastTimestamp = useRef(null);
  const logRef = useRef(null);

  // New messages are fetched every few seconds while this tab is visible. (Polling - not a live socket.)
  const mergeIncoming = useCallback((incoming) => {
    if (!incoming.length) return;
    setMessages((previous) => {
      const known = new Set(previous.map((m) => m.id));
      const fresh = incoming.filter((m) => !known.has(m.id));
      return fresh.length ? [...previous, ...fresh] : previous;
    });
    lastTimestamp.current = incoming[incoming.length - 1].created_at;
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const poll = () => listMessages(groupId, lastTimestamp.current, controller.signal)
      .then((data) => { mergeIncoming(data.messages || []); setError(""); setLoaded(true); })
      .catch((err) => { if (!isAbort(err)) { setError(err.message); setLoaded(true); } });
    poll();
    const timer = setInterval(() => { if (document.visibilityState === "visible") poll(); }, CHAT_POLL_MS);
    return () => { controller.abort(); clearInterval(timer); };
  }, [groupId, mergeIncoming]);

  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [messages.length]);

  async function handleSend(event) {
    event.preventDefault();
    const body = text.trim();
    if (!body || sending) return;
    setSending(true);
    try {
      const { message } = await sendMessage(groupId, body);
      mergeIncoming([message]);
      setText("");
      setError("");
    } catch (err) {
      setError(err.message);            // the text stays in the box so nothing the user typed is lost
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="ts-card chat" aria-labelledby="chat-heading">
      <h2 id="chat-heading">Group chat</h2>
      <p className="ts-muted ts-small">Updates every few seconds while this page is open.</p>
      <ul className="chat__log" ref={logRef} role="log" aria-live="polite" aria-label="Chat messages">
        {!loaded && <li className="ts-muted">Loading messages…</li>}
        {loaded && messages.length === 0 && <li className="ts-muted">No messages yet. Say hello 👋</li>}
        {messages.map((m) => (
          <li key={m.id} className={`chat__msg${m.is_me ? " is-me" : ""}`}>
            <small>{m.is_me ? "You" : m.author} · {clock(m.created_at)}</small>
            {m.text}
          </li>
        ))}
      </ul>
      {error && <div className="ts-alert ts-alert--error" role="alert">{error}</div>}
      <form className="chat__form" onSubmit={handleSend}>
        <input value={text} onChange={(e) => setText(e.target.value)} maxLength={1000} placeholder="Write a message…" aria-label="Message" />
        <button type="submit" className="btn btn--primary" disabled={sending || !text.trim()} aria-label="Send message"><Send size={16} /></button>
      </form>
    </section>
  );
}

function SuggestionForm({ groupId, onAdded }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [picked, setPicked] = useState(null);
  const [note, setNote] = useState("");
  const [budget, setBudget] = useState("");
  const [duration, setDuration] = useState("");
  const [features, setFeatures] = useState([]);
  const [chosen, setChosen] = useState([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    getFeatures().then((data) => active && setFeatures(data.interest_features || [])).catch(() => {});
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      if (!query.trim() || picked) { setResults([]); return; }
      try { const data = await searchDestinations(query, controller.signal); setResults(data.results || []); }
      catch (err) { if (!isAbort(err)) setResults([]); }
    }, 220);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, picked]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (saving) return;
    setError("");
    if (!picked) return setError("Choose a destination from the suggestions.");
    const payload = { destination: picked.Destination, note: note.trim(), preferences: chosen };
    if (budget !== "") {
      const parsed = parsePositiveInteger(budget, { label: "the budget", max: MAX_BUDGET_INR });
      if (!parsed.ok) return setError(parsed.error);
      payload.budget = parsed.value;
    }
    if (duration !== "") {
      const parsed = parsePositiveInteger(duration, { label: "the duration", max: MAX_DURATION_DAYS, unit: " days" });
      if (!parsed.ok) return setError(parsed.error);
      payload.duration = parsed.value;
    }
    setSaving(true);
    try {
      await addSuggestion(groupId, payload);
      setQuery(""); setPicked(null); setNote(""); setBudget(""); setDuration(""); setChosen([]);
      await onAdded();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="ts-form ts-form--wide" onSubmit={handleSubmit} noValidate>
      <div className="ts-field">
        <label htmlFor="sg-destination">Destination</label>
        <input id="sg-destination" value={query} autoComplete="off" placeholder="Search a destination" onChange={(e) => { setQuery(e.target.value); setPicked(null); }} />
        {query && !picked && results.length > 0 && (
          <div className="dest-results">
            {results.map((item) => (
              <button type="button" key={`${item.Destination}-${item.State}`} onClick={() => { setPicked(item); setQuery(item.Destination); setResults([]); }}>
                <strong>{item.Destination}</strong> <span className="ts-muted">{item.State}</span>
              </button>
            ))}
          </div>
        )}
        {picked && <span className="ts-hint"><Check size={12} aria-hidden="true" /> {picked.Destination}, {picked.State}</span>}
      </div>
      <div className="ts-field">
        <label htmlFor="sg-budget">Budget (optional)</label>
        <div className="ts-input-unit"><b>₹</b><NumberField id="sg-budget" value={budget} maxLength={8} onChange={setBudget} placeholder="per trip" /></div>
      </div>
      <div className="ts-field">
        <label htmlFor="sg-duration">Duration (optional)</label>
        <div className="ts-input-unit"><NumberField id="sg-duration" value={duration} maxLength={2} onChange={setDuration} placeholder="e.g. 4" /><b>days</b></div>
      </div>
      <div className="ts-field" style={{ gridColumn: "1 / -1" }}>
        <label htmlFor="sg-note">Why this place? (optional)</label>
        <textarea id="sg-note" value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} />
      </div>
      {features.length > 0 && (
        <div className="ts-field" style={{ gridColumn: "1 / -1" }} role="group" aria-labelledby="sg-prefs-label">
          <span className="ts-label" id="sg-prefs-label">Preferences it fits (optional)</span>
          <div className="interest-picker">
            {features.map((f) => (
              <button type="button" key={f} aria-pressed={chosen.includes(f)} onClick={() => setChosen((c) => (c.includes(f) ? c.filter((x) => x !== f) : c.length < 12 ? [...c, f] : c))}>{f}</button>
            ))}
          </div>
        </div>
      )}
      {error && <div className="ts-alert ts-alert--error" role="alert" style={{ gridColumn: "1 / -1" }}>{error}</div>}
      <div className="ts-actions" style={{ gridColumn: "1 / -1" }}>
        <button type="submit" className="btn btn--primary" disabled={saving}>{saving ? "Sharing…" : "Share with the group"}</button>
      </div>
    </form>
  );
}

export default function GroupDetail() {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState({ groupId: null, status: "loading", group: null, suggestions: [], error: "" });
  const [reloadKey, setReloadKey] = useState(0);
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([getGroup(groupId), listSuggestions(groupId)])
      .then(([g, s]) => active && setState({ groupId, status: "ready", group: g.group, suggestions: s.suggestions || [], error: "" }))
      .catch((err) => active && setState({ groupId, status: err.kind === "notfound" ? "missing" : "error", group: null, suggestions: [], error: err.message }));
    return () => { active = false; };
  }, [groupId, reloadKey]);

  // Keep votes/suggestions current for everyone while the page is open.
  useEffect(() => {
    const timer = setInterval(() => {
      if (document.visibilityState !== "visible") return;
      Promise.all([getGroup(groupId), listSuggestions(groupId)])
        .then(([g, s]) => setState((prev) => (prev.groupId === groupId && prev.status === "ready" ? { ...prev, group: g.group, suggestions: s.suggestions || [] } : prev)))
        .catch(() => {});
    }, SUGGESTION_POLL_MS);
    return () => clearInterval(timer);
  }, [groupId]);

  const current = state.groupId === groupId ? state : { status: "loading" };
  const { group, suggestions } = current;

  const refresh = useCallback(async () => {
    const [g, s] = await Promise.all([getGroup(groupId), listSuggestions(groupId)]);
    setState({ groupId, status: "ready", group: g.group, suggestions: s.suggestions || [], error: "" });
  }, [groupId]);

  async function run(label, action) {
    if (busy) return;
    setBusy(label); setActionError("");
    try { await action(); } catch (err) { setActionError(err.message); } finally { setBusy(""); }
  }

  const applySuggestions = (data) => setState((prev) => ({ ...prev, suggestions: data.suggestions || prev.suggestions }));

  const handleVote = (s) => run(`vote-${s.id}`, async () => applySuggestions(await (s.voted_by_me ? removeVote(groupId, s.id) : vote(groupId, s.id))));
  const handleRemove = (s) => run(`rm-${s.id}`, async () => { await deleteSuggestion(groupId, s.id); await refresh(); });
  const handleDecide = (s) => run(`decide-${s.id}`, async () => { await decide(groupId, s.id); await refresh(); });
  const handleReopen = () => run("reopen", async () => { await reopenVoting(groupId); await refresh(); });
  const handleLeave = () => run("leave", async () => {
    if (!window.confirm("Leave this group? Your vote will be removed.")) return;
    await leaveGroup(groupId); navigate("/groups", { replace: true });
  });
  const handleDelete = () => run("delete", async () => {
    if (!window.confirm("Delete this group for everyone? Chat, suggestions and votes will be removed. This can't be undone.")) return;
    await deleteGroup(groupId); navigate("/groups", { replace: true });
  });
  const handleCreateTrip = (s) => run(`trip-${s.id}`, async () => {
    const { trip } = await createTrip({ destination: s.destination, duration: s.duration || undefined, budget: s.budget || undefined, source: "group-vote", group_id: groupId });
    navigate(`/trip/${trip.id}`);
  });

  async function copyCode() {
    try { await navigator.clipboard.writeText(group.invite_code); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    catch { setActionError("Couldn't copy automatically. Select the code and copy it manually."); }
  }

  const back = <Link className="packing-back" to="/groups"><ArrowLeft size={16} /> All groups</Link>;

  if (current.status === "loading") return <main className="dashboard__content"><div className="ts-empty" role="status">Loading group…</div></main>;
  if (current.status === "missing") {
    return <main className="dashboard__content">{back}<div className="ts-empty"><h3>Group not found</h3><p>It may have been deleted, or you may not be a member.</p></div></main>;
  }
  if (current.status === "error") {
    return (
      <main className="dashboard__content">{back}
        <div className="ts-alert ts-alert--error" role="alert">
          {current.error} <button type="button" className="notif__link" onClick={() => { setState((p) => ({ ...p, groupId: null })); setReloadKey((k) => k + 1); }}>Try again</button>
        </div>
      </main>
    );
  }

  const decided = suggestions.find((s) => s.is_decision);

  return (
    <main className="dashboard__content">
      {back}
      <div className="ts-page-head">
        <span className="dashboard__eyebrow">TRAVEL GROUP</span>
        <h1>{group.name}</h1>
        {group.description && <p>{group.description}</p>}
      </div>

      {actionError && <div className="ts-alert ts-alert--error" role="alert">{actionError}</div>}

      <section className="ts-card" aria-labelledby="members-heading">
        <h2 id="members-heading"><Users size={18} aria-hidden="true" /> Members ({group.member_count})</h2>
        <ul className="group-members">
          {group.members.map((m) => (
            <li key={m.id} className={`ts-chip${m.is_owner ? " ts-chip--peach" : ""}`}>{m.is_owner && <Crown size={12} aria-hidden="true" />} {m.name}{m.is_me ? " (you)" : ""}</li>
          ))}
        </ul>
        <div className="group-invite">
          <span className="ts-muted">Invite code:</span> <code>{group.invite_code}</code>
          <button type="button" className="ts-btn-secondary" onClick={copyCode}><Copy size={14} aria-hidden="true" /> {copied ? "Copied" : "Copy"}</button>
        </div>
        <p className="ts-hint" style={{ marginTop: 8 }}>Anyone with this code can join, so share it only with people you trust.</p>
        <div className="ts-actions" style={{ marginTop: 12 }}>
          {group.is_owner
            ? <button type="button" className="ts-btn-secondary ts-btn-danger" onClick={handleDelete} disabled={Boolean(busy)}><Trash2 size={14} aria-hidden="true" /> Delete group</button>
            : <button type="button" className="ts-btn-secondary ts-btn-danger" onClick={handleLeave} disabled={Boolean(busy)}>Leave group</button>}
        </div>
      </section>

      <div className="group-layout">
        <div>
          {decided && (
            <div className="ts-alert ts-alert--success" role="status">
              <strong>The group chose {decided.destination}.</strong> Voting is closed.
              {group.is_owner && <> <button type="button" className="notif__link" onClick={handleReopen} disabled={Boolean(busy)}>Reopen voting</button></>}
            </div>
          )}

          <section className="ts-card" aria-labelledby="suggest-heading">
            <h2 id="suggest-heading">Suggest a destination</h2>
            <p className="ts-muted">Share a place with the group so everyone can discuss it and vote.</p>
            <SuggestionForm groupId={groupId} onAdded={refresh} />
          </section>

          <section className="ts-card" aria-labelledby="votes-heading">
            <h2 id="votes-heading">Destination ideas &amp; votes</h2>
            <p className="ts-muted">Each member has one vote. Voting for another idea moves your vote.</p>
            {suggestions.length === 0 ? (
              <div className="ts-empty"><h3>No suggestions yet</h3><p>Be the first to suggest a destination.</p></div>
            ) : (
              <ul className="suggestions-list">
                {suggestions.map((s) => (
                  <li key={s.id} className={`suggestion${s.is_decision ? " is-decision" : ""}`}>
                    <div className="suggestion__head">
                      <div><h3>{s.destination}</h3><span className="ts-muted ts-small">{s.state} · suggested by {s.proposed_by_me ? "you" : s.proposed_by}</span></div>
                      {s.is_decision && <span className="ts-chip ts-chip--aqua"><Check size={12} aria-hidden="true" /> Chosen</span>}
                    </div>
                    {s.note && <p>{s.note}</p>}
                    <div className="suggestion__chips">
                      {s.budget && <span className="ts-chip">{inr(s.budget)}</span>}
                      {s.duration && <span className="ts-chip">{s.duration} days</span>}
                      {s.preferences.map((p) => <span key={p} className="ts-chip ts-chip--peach">{p}</span>)}
                    </div>
                    {s.places.length > 0 && <p className="suggestion__places">Top places: {s.places.join(" · ")}</p>}
                    <div className="ts-actions">
                      <button type="button" className="vote-btn" aria-pressed={s.voted_by_me} onClick={() => handleVote(s)} disabled={Boolean(decided) || Boolean(busy)}
                        aria-label={`${s.voted_by_me ? "Remove your vote from" : "Vote for"} ${s.destination}. ${s.votes} ${s.votes === 1 ? "vote" : "votes"}`}>
                        <ThumbsUp size={14} aria-hidden="true" /> {s.voted_by_me ? "Voted" : "Vote"} · {s.votes}
                      </button>
                      {group.is_owner && !decided && <button type="button" className="ts-btn-secondary" onClick={() => handleDecide(s)} disabled={Boolean(busy)}>Choose this destination</button>}
                      {s.is_decision && <button type="button" className="btn btn--primary" onClick={() => handleCreateTrip(s)} disabled={Boolean(busy)}>Create my trip</button>}
                      {(s.proposed_by_me || group.is_owner) && !s.is_decision && (
                        <button type="button" className="ts-btn-secondary ts-btn-danger" onClick={() => handleRemove(s)} disabled={Boolean(busy)} aria-label={`Remove suggestion ${s.destination}`}><Trash2 size={14} aria-hidden="true" /></button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <Chat groupId={groupId} />
      </div>
    </main>
  );
}
