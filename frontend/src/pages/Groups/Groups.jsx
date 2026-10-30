import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Users } from "lucide-react";
import { createGroup, joinGroup, listGroups } from "../../services/groupApi";
import "../../styles/appPages.css";
import "./Groups.css";

export default function Groups() {
  const navigate = useNavigate();
  const [state, setState] = useState({ status: "loading", groups: [], error: "" });
  const [reloadKey, setReloadKey] = useState(0);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [code, setCode] = useState("");
  const [createError, setCreateError] = useState("");
  const [joinError, setJoinError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    let active = true;
    listGroups()
      .then((data) => active && setState({ status: "ready", groups: data.groups || [], error: "" }))
      .catch((err) => active && setState({ status: "error", groups: [], error: err.message }));
    return () => { active = false; };
  }, [reloadKey]);

  async function handleCreate(event) {
    event.preventDefault();
    if (busy) return;
    setCreateError("");
    const trimmed = name.trim();
    if (trimmed.length < 2) return setCreateError("Give your group a name (at least 2 characters).");
    setBusy("create");
    try {
      const { group } = await createGroup(trimmed, description.trim());
      navigate(`/groups/${group.id}`);
    } catch (err) {
      setCreateError(err.message);
      setBusy("");
    }
  }

  async function handleJoin(event) {
    event.preventDefault();
    if (busy) return;
    setJoinError("");
    const trimmed = code.trim();
    if (!/^[A-Za-z0-9_-]{4,40}$/.test(trimmed)) return setJoinError("Enter the invite code exactly as it was shared with you.");
    setBusy("join");
    try {
      const { group } = await joinGroup(trimmed);
      navigate(`/groups/${group.id}`);
    } catch (err) {
      setJoinError(err.message);
      setBusy("");
    }
  }

  return (
    <main className="dashboard__content">
      <div className="ts-page-head">
        <span className="dashboard__eyebrow">COLLABORATIVE TRAVEL HUB</span>
        <h1>Travel groups</h1>
        <p>Plan with friends and family: chat, share destination ideas, vote, and settle on a place together.</p>
      </div>

      <div className="groups-forms">
        <section className="ts-card" aria-labelledby="create-group-heading">
          <h2 id="create-group-heading">Create a group</h2>
          <form className="ts-form" onSubmit={handleCreate} noValidate>
            <div className="ts-field">
              <label htmlFor="group-name">Group name</label>
              <input id="group-name" value={name} maxLength={60} onChange={(e) => setName(e.target.value)} placeholder="e.g. Goa gang 2027" />
            </div>
            <div className="ts-field">
              <label htmlFor="group-description">Description <span className="ts-hint">(optional)</span></label>
              <input id="group-description" value={description} maxLength={300} onChange={(e) => setDescription(e.target.value)} />
            </div>
            {createError && <div className="ts-alert ts-alert--error" role="alert">{createError}</div>}
            <div className="ts-actions"><button type="submit" className="btn btn--primary" disabled={busy === "create"}><Plus size={16} /> {busy === "create" ? "Creating…" : "Create group"}</button></div>
          </form>
        </section>

        <section className="ts-card" aria-labelledby="join-group-heading">
          <h2 id="join-group-heading">Join a group</h2>
          <p className="ts-muted">Ask a group member for the invite code shown on their group page.</p>
          <form className="ts-form" onSubmit={handleJoin} noValidate>
            <div className="ts-field">
              <label htmlFor="invite-code">Invite code</label>
              <input id="invite-code" value={code} maxLength={40} autoComplete="off" onChange={(e) => setCode(e.target.value)} />
            </div>
            {joinError && <div className="ts-alert ts-alert--error" role="alert">{joinError}</div>}
            <div className="ts-actions"><button type="submit" className="btn btn--primary" disabled={busy === "join"}>{busy === "join" ? "Joining…" : "Join group"}</button></div>
          </form>
        </section>
      </div>

      <h2 className="groups-list-heading">Your groups</h2>
      {state.status === "loading" ? (
        <div className="ts-empty" role="status">Loading your groups…</div>
      ) : state.status === "error" ? (
        <div className="ts-alert ts-alert--error" role="alert">
          {state.error} <button type="button" className="notif__link" onClick={() => { setState({ status: "loading", groups: [], error: "" }); setReloadKey((k) => k + 1); }}>Try again</button>
        </div>
      ) : state.groups.length === 0 ? (
        <div className="ts-empty"><Users size={26} /><h3>No groups yet</h3><p>Create one above, or join with an invite code.</p></div>
      ) : (
        <ul className="ts-grid groups-grid">
          {state.groups.map((group) => (
            <li key={group.id}>
              <Link to={`/groups/${group.id}`} className="group-card">
                <strong>{group.name}</strong>
                {group.description && <span className="ts-muted">{group.description}</span>}
                <span className="ts-chip"><Users size={13} aria-hidden="true" /> {group.member_count} {group.member_count === 1 ? "member" : "members"}</span>
                {group.is_owner && <span className="ts-chip ts-chip--peach">Owner</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
