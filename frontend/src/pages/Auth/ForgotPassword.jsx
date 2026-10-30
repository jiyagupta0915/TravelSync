import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword, getRecoveryStatus } from "../../services/authApi";
import AuthPanel from "./AuthPanel";
import "./Auth.css";

export default function ForgotPassword() {
  const [available, setAvailable] = useState(null);     // null = still checking
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    getRecoveryStatus()
      .then((data) => active && setAvailable(Boolean(data.available)))
      .catch(() => active && setAvailable(null));
    return () => { active = false; };
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;
    setError(""); setMessage("");
    if (!email.trim()) { setError("Enter the email address of your account."); return; }
    setIsSubmitting(true);
    try {
      const data = await forgotPassword(email.trim());
      setMessage(data.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth">
      <AuthPanel heading="Locked out?" text="We can email you a link to choose a new password." />
      <div className="auth__form-side">
        <div className="auth-card">
          <h1>Reset your password</h1>
          <p className="auth-card__subtext">Enter your account email and we'll send you a reset link.</p>

          {available === false ? (
            <>
              <p className="auth-form__notice" role="status">
                Password recovery by email isn't available on this server yet because email delivery hasn't been configured.
                Please contact the person who runs this TravelSync site, or use the change-password option in Settings while you're logged in.
              </p>
              <p className="auth-card__footer"><Link to="/login">Back to log in</Link></p>
            </>
          ) : (
            <>
              <form className="auth-form" onSubmit={handleSubmit} noValidate>
                <div className="form-field">
                  <label htmlFor="email">Email</label>
                  <input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
                </div>
                {error && <p className="auth-form__error" role="alert">{error}</p>}
                {message && <p className="auth-form__success" role="status">{message}</p>}
                <button type="submit" className="btn btn--primary auth-form__submit" disabled={isSubmitting}>
                  {isSubmitting ? "Sending..." : "Send reset link"}
                </button>
              </form>
              <p className="auth-card__footer"><Link to="/login">Back to log in</Link></p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
