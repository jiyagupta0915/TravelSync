import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import PasswordInput from "../../components/PasswordInput/PasswordInput";
import PasswordRequirements from "../../components/PasswordRequirements/PasswordRequirements";
import { resetPassword } from "../../services/authApi";
import { checkPassword } from "../../utils/passwordPolicy";
import AuthPanel from "./AuthPanel";
import "./Auth.css";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const mismatch = confirm && password !== confirm;

  async function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;
    setError("");
    if (!checkPassword(password).valid) { setError("Your password doesn't meet all the requirements yet."); return; }
    if (password !== confirm) { setError("Passwords do not match."); return; }
    setIsSubmitting(true);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth">
      <AuthPanel heading="Choose a new password." text="Pick something strong that you don't use anywhere else." />
      <div className="auth__form-side">
        <div className="auth-card">
          <h1>New password</h1>
          {!token ? (
            <>
              <p className="auth-form__error" role="alert">This reset link is incomplete. Please request a new one.</p>
              <p className="auth-card__footer"><Link to="/forgot-password">Request a new link</Link></p>
            </>
          ) : done ? (
            <>
              <p className="auth-form__success" role="status">Your password has been updated.</p>
              <p className="auth-card__footer"><Link to="/login">Log in with your new password</Link></p>
            </>
          ) : (
            <form className="auth-form" onSubmit={handleSubmit} noValidate>
              <div className="form-field">
                <PasswordInput id="new-password" label="New password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" describedBy="reset-requirements" />
                <PasswordRequirements id="reset-requirements" password={password} />
              </div>
              <div className="form-field">
                <PasswordInput id="confirm-new-password" label="Confirm new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" invalid={Boolean(mismatch)} describedBy={mismatch ? "reset-mismatch" : undefined} />
                {mismatch && <p className="field-error" id="reset-mismatch" role="alert">Passwords do not match.</p>}
              </div>
              {error && <p className="auth-form__error" role="alert">{error}</p>}
              <button type="submit" className="btn btn--primary auth-form__submit" disabled={isSubmitting}>
                {isSubmitting ? "Saving..." : "Set new password"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
