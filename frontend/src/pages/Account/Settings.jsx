import { useState } from "react";
import { useAuth } from "../../context/useAuth";
import NumberField from "../../components/NumberField/NumberField";
import { saveSettings } from "../../services/userApi";
import { MAX_BUDGET_INR, MAX_DURATION_DAYS, TRAVELLER_TYPES } from "../../utils/limits";
import { parsePositiveInteger } from "../../utils/numberField";
import "../../styles/appPages.css";

function SettingsForm({ settings, updateUser }) {
  const [traveller, setTraveller] = useState(settings.default_traveller_type || "");
  const [duration, setDuration] = useState(settings.default_duration_days ? String(settings.default_duration_days) : "");
  const [budget, setBudget] = useState(settings.default_budget_inr ? String(settings.default_budget_inr) : "");
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState({ type: "", text: "" });
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (saving) return;
    const nextErrors = {};
    const payload = { default_traveller_type: traveller || null, default_duration_days: null, default_budget_inr: null };
    if (duration !== "") {
      const parsed = parsePositiveInteger(duration, { label: "the default duration", max: MAX_DURATION_DAYS, unit: " days" });
      if (parsed.ok) payload.default_duration_days = parsed.value; else nextErrors.duration = parsed.error;
    }
    if (budget !== "") {
      const parsed = parsePositiveInteger(budget, { label: "the default budget", max: MAX_BUDGET_INR });
      if (parsed.ok) payload.default_budget_inr = parsed.value; else nextErrors.budget = parsed.error;
    }
    setErrors(nextErrors);
    setMessage({ type: "", text: "" });
    if (Object.keys(nextErrors).length) return;

    setSaving(true);
    try {
      const saved = await saveSettings(payload);
      updateUser({ settings: saved });               // the planner forms read these straight away
      setMessage({ type: "success", text: "Settings saved. New trip forms will start with these values." });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  }

  function clearAll() {
    setTraveller(""); setDuration(""); setBudget(""); setErrors({}); setMessage({ type: "", text: "" });
  }

  return (
    <form className="ts-form" onSubmit={handleSubmit} noValidate>
      <div className="ts-field">
        <label htmlFor="set-traveller">Usual travelling party</label>
        <select id="set-traveller" value={traveller} onChange={(e) => setTraveller(e.target.value)}>
          <option value="">No default</option>
          {TRAVELLER_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
        </select>
      </div>
      <div className="ts-field">
        <label htmlFor="set-duration">Usual trip length</label>
        <div className="ts-input-unit">
          <NumberField id="set-duration" value={duration} maxLength={2} onChange={setDuration} invalid={Boolean(errors.duration)} describedBy="set-duration-hint" placeholder="e.g. 5" /><b>days</b>
        </div>
        <span className="ts-hint" id="set-duration-hint">Between 1 and {MAX_DURATION_DAYS} days. Leave empty for no default.</span>
        {errors.duration && <span className="ts-error" role="alert">{errors.duration}</span>}
      </div>
      <div className="ts-field">
        <label htmlFor="set-budget">Usual total budget</label>
        <div className="ts-input-unit">
          <b>₹</b><NumberField id="set-budget" value={budget} maxLength={8} onChange={setBudget} invalid={Boolean(errors.budget)} describedBy="set-budget-hint" placeholder="e.g. 20000" />
        </div>
        <span className="ts-hint" id="set-budget-hint">Leave empty for no default.</span>
        {errors.budget && <span className="ts-error" role="alert">{errors.budget}</span>}
      </div>
      {message.text && <div className={`ts-alert ts-alert--${message.type}`} role={message.type === "error" ? "alert" : "status"}>{message.text}</div>}
      <div className="ts-actions">
        <button type="submit" className="btn btn--primary" disabled={saving}>{saving ? "Saving…" : "Save settings"}</button>
        <button type="button" className="ts-btn-secondary" onClick={clearAll} disabled={saving}>Clear fields</button>
      </div>
    </form>
  );
}

export default function Settings() {
  const { user, updateUser } = useAuth();
  return (
    <main className="dashboard__content">
      <div className="ts-page-head">
        <span className="dashboard__eyebrow">YOUR ACCOUNT</span>
        <h1>Settings</h1>
        <p>Trip defaults. They pre-fill the destination finder and the "I know my destination" form so you don't retype them. Nothing is applied until you save.</p>
      </div>
      <section className="ts-card" aria-labelledby="defaults-heading">
        <h2 id="defaults-heading">Trip planning defaults</h2>
        <p className="ts-muted">You can still change any value on each form.</p>
        <SettingsForm key={user?.id} settings={user?.settings || {}} updateUser={updateUser} />
      </section>
    </main>
  );
}
