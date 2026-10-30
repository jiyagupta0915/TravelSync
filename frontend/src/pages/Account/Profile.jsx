import { useState } from "react";
import { useAuth } from "../../context/useAuth";
import PasswordInput from "../../components/PasswordInput/PasswordInput";
import PasswordRequirements from "../../components/PasswordRequirements/PasswordRequirements";
import { updateProfile } from "../../services/userApi";
import { changePassword } from "../../services/authApi";
import { checkPassword } from "../../utils/passwordPolicy";
import { getDisplayName, getInitials } from "../../utils/userDisplay";
import "../../styles/appPages.css";

function ProfileForm({ user, updateUser }) {
  const [name, setName] = useState(user.name || "");
  const [homeCity, setHomeCity] = useState(user.home_city || "");
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState({ type: "", text: "" });
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (saving) return;
    const nextErrors = {};
    const trimmedName = name.trim();
    if (trimmedName.length < 2) nextErrors.name = "Enter your name (at least 2 characters).";
    if (trimmedName.length > 80) nextErrors.name = "Your name can be at most 80 characters.";
    if (homeCity.trim().length === 1 || homeCity.trim().length > 80) nextErrors.home_city = "Home city must be 2–80 characters (or leave it empty).";
    setErrors(nextErrors);
    setMessage({ type: "", text: "" });
    if (Object.keys(nextErrors).length) return;

    setSaving(true);
    try {
      const saved = await updateProfile({ name: trimmedName, home_city: homeCity.trim() });
      updateUser({ name: saved.name, home_city: saved.home_city });
      setName(saved.name); setHomeCity(saved.home_city || "");
      setMessage({ type: "success", text: "Profile saved." });
    } catch (err) {
      setErrors({ name: err.fieldErrors?.name, home_city: err.fieldErrors?.home_city });
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="ts-form" onSubmit={handleSubmit} noValidate>
      <div className="ts-field">
        <label htmlFor="profile-name">Full name</label>
        <input id="profile-name" value={name} maxLength={80} autoComplete="name" onChange={(e) => setName(e.target.value)}
          aria-invalid={Boolean(errors.name) || undefined} aria-describedby={errors.name ? "profile-name-error" : undefined} />
        {errors.name && <span className="ts-error" id="profile-name-error">{errors.name}</span>}
      </div>
      <div className="ts-field">
        <label htmlFor="profile-email">Email</label>
        <input id="profile-email" value={user.email || ""} readOnly aria-describedby="profile-email-hint" />
        <span className="ts-hint" id="profile-email-hint">Your email is your login and can't be changed here.</span>
      </div>
      <div className="ts-field">
        <label htmlFor="profile-city">Home city <span className="ts-hint">(optional)</span></label>
        <input id="profile-city" value={homeCity} maxLength={80} autoComplete="address-level2" onChange={(e) => setHomeCity(e.target.value)}
          aria-invalid={Boolean(errors.home_city) || undefined} aria-describedby={errors.home_city ? "profile-city-error" : undefined} />
        {errors.home_city && <span className="ts-error" id="profile-city-error">{errors.home_city}</span>}
      </div>
      {message.text && <div className={`ts-alert ts-alert--${message.type}`} role={message.type === "error" ? "alert" : "status"}>{message.text}</div>}
      <div className="ts-actions"><button type="submit" className="btn btn--primary" disabled={saving}>{saving ? "Saving…" : "Save profile"}</button></div>
    </form>
  );
}

function PasswordForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState({ type: "", text: "" });
  const [saving, setSaving] = useState(false);
  const mismatch = confirm && next !== confirm;

  async function handleSubmit(event) {
    event.preventDefault();
    if (saving) return;
    setMessage({ type: "", text: "" });
    if (!current) return setMessage({ type: "error", text: "Enter your current password." });
    if (!checkPassword(next).valid) return setMessage({ type: "error", text: "Your new password doesn't meet all the requirements yet." });
    if (next !== confirm) return setMessage({ type: "error", text: "The new passwords do not match." });
    if (next === current) return setMessage({ type: "error", text: "Your new password must be different from the current one." });

    setSaving(true);
    try {
      const data = await changePassword(current, next);
      setCurrent(""); setNext(""); setConfirm("");
      setMessage({ type: "success", text: data.message || "Password updated." });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="ts-form" onSubmit={handleSubmit} noValidate>
      <PasswordInput id="current-password" label="Current password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
      <div className="ts-field">
        <PasswordInput id="new-password" label="New password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" describedBy="change-requirements" />
        <PasswordRequirements id="change-requirements" password={next} />
      </div>
      <div className="ts-field">
        <PasswordInput id="confirm-password" label="Confirm new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" invalid={Boolean(mismatch)} describedBy={mismatch ? "change-mismatch" : undefined} />
        {mismatch && <span className="ts-error" id="change-mismatch" role="alert">Passwords do not match.</span>}
      </div>
      {message.text && <div className={`ts-alert ts-alert--${message.type}`} role={message.type === "error" ? "alert" : "status"}>{message.text}</div>}
      <div className="ts-actions"><button type="submit" className="btn btn--primary" disabled={saving}>{saving ? "Updating…" : "Change password"}</button></div>
    </form>
  );
}

export default function Profile() {
  const { user, updateUser } = useAuth();
  return (
    <main className="dashboard__content">
      <div className="ts-page-head">
        <span className="dashboard__eyebrow">YOUR ACCOUNT</span>
        <h1>Profile</h1>
        <p>Your name appears to your travel group members. Your email stays private.</p>
      </div>

      <section className="ts-card" aria-labelledby="profile-heading">
        <div className="ts-identity">
          <span className="ts-identity__avatar" aria-hidden="true">{getInitials(user)}</span>
          <div><strong>{getDisplayName(user)}</strong><span className="ts-muted">{user?.email}</span></div>
        </div>
        <h2 id="profile-heading" className="sr-only">Edit profile</h2>
        {/* keyed on the user id so the form starts from the saved values */}
        <ProfileForm key={user?.id} user={user} updateUser={updateUser} />
      </section>

      <section className="ts-card" aria-labelledby="password-heading">
        <h2 id="password-heading">Change password</h2>
        <p className="ts-muted">Changing your password signs you out of your other devices.</p>
        <PasswordForm />
      </section>
    </main>
  );
}
