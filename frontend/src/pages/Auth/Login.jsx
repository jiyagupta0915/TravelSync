import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import PasswordInput from "../../components/PasswordInput/PasswordInput";
import "./Auth.css";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await login(email, password);
      navigate("/home");
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth">
      <aside className="auth__panel">
        <Link to="/" className="auth__brand">
          TravelSync
        </Link>

        <div className="auth__panel-content">
          <h2>Your next adventure is waiting.</h2>
          <p>Log back in to pick up your trip planning right where you left off.</p>
        </div>

        <div className="auth__panel-visual" aria-hidden="true">
          <svg viewBox="0 0 200 160" className="auth__panel-svg">
            <path
              d="M20 130 C 60 100, 90 110, 110 70 S 160 30, 180 15"
              stroke="var(--ink)"
              strokeWidth="2"
              strokeDasharray="6 9"
              strokeLinecap="round"
              fill="none"
            />
            <circle cx="20" cy="130" r="5" fill="var(--ink)" />
            <circle cx="180" cy="15" r="5" fill="var(--ink)" />
          </svg>
        </div>
      </aside>

      <div className="auth__form-side">
        <div className="auth-card">
          <h1>Welcome back</h1>
          <p className="auth-card__subtext">Log in to continue planning your trips.</p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="form-field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </div>

            <PasswordInput
              id="password"
              label="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />

            <div className="auth-form__meta">
              <a href="#forgot-password">Forgot password?</a>
            </div>

            {error && <p className="auth-form__error">{error}</p>}

            <button type="submit" className="btn btn--primary auth-form__submit" disabled={isSubmitting}>
              {isSubmitting ? "Logging in..." : "Log In"}
            </button>
          </form>

          <p className="auth-card__footer">
            Don't have an account? <Link to="/signup">Sign Up</Link>
          </p>
        </div>
      </div>
    </div>
  );
}