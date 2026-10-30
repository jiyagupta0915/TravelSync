import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/useAuth";
import PasswordInput from "../../components/PasswordInput/PasswordInput";
import AuthPanel from "./AuthPanel";
import "./Auth.css";

// Only follow same-site paths after login (never an absolute URL someone put in the state).
function safeRedirect(from) {
  return typeof from === "string" && from.startsWith("/") && !from.startsWith("//") ? from : "/home";
}

export default function Login() {
  const { login, status } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = safeRedirect(location.state?.from);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (status === "authenticated") return <Navigate to={redirectTo} replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;
    setError("");
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    setIsSubmitting(true);
    try {
      // No password-policy check here on purpose: existing users with older passwords must still be able to sign in.
      await login(email.trim(), password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth">
      <AuthPanel heading="Your next adventure is waiting." text="Log back in to pick up your trip planning right where you left off." />

      <div className="auth__form-side">
        <div className="auth-card">
          <h1>Welcome back</h1>
          <p className="auth-card__subtext">Log in to continue planning your trips.</p>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div className="form-field">
              <label htmlFor="email">Email</label>
              <input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
            </div>

            <PasswordInput id="password" label="Password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" autoComplete="current-password" />

            <div className="auth-form__meta">
              <Link to="/forgot-password">Forgot password?</Link>
            </div>

            {error && <p className="auth-form__error" role="alert">{error}</p>}

            <button type="submit" className="btn btn--primary auth-form__submit" disabled={isSubmitting}>
              {isSubmitting ? "Logging in..." : "Log In"}
            </button>
          </form>

          <p className="auth-card__footer">Don't have an account? <Link to="/signup">Sign Up</Link></p>
        </div>
      </div>
    </div>
  );
}
