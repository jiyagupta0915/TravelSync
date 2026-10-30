import { useRef, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/useAuth";
import PasswordInput from "../../components/PasswordInput/PasswordInput";
import PasswordRequirements from "../../components/PasswordRequirements/PasswordRequirements";
import { checkPassword } from "../../utils/passwordPolicy";
import AuthPanel from "./AuthPanel";
import "./Auth.css";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function validate({ fullName, email, password, confirmPassword }) {
  const errors = {};
  const name = fullName.trim();
  if (name.length < 2) errors.name = "Enter your full name (at least 2 characters).";
  else if (!/\p{L}/u.test(name)) errors.name = "Your name must contain at least one letter.";
  if (!email.trim()) errors.email = "Enter your email address.";
  else if (!EMAIL_PATTERN.test(email.trim())) errors.email = "Enter a valid email address.";
  if (!checkPassword(password).valid) errors.password = "Your password doesn't meet all the requirements yet.";
  if (!confirmPassword) errors.confirmPassword = "Re-enter your password.";
  else if (password !== confirmPassword) errors.confirmPassword = "Passwords do not match.";
  return errors;
}

export default function Signup() {
  const { signup, status } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const nameRef = useRef(null);
  const emailRef = useRef(null);
  const passwordRef = useRef(null);
  const confirmRef = useRef(null);

  if (status === "authenticated") return <Navigate to="/home" replace />;

  // The live "do the two passwords match?" message appears as soon as the user starts typing the confirmation.
  const liveConfirmError = confirmPassword && password !== confirmPassword ? "Passwords do not match." : "";

  function focusFirstInvalid(errors) {
    const order = [["name", nameRef], ["email", emailRef], ["password", passwordRef], ["confirmPassword", confirmRef]];
    const first = order.find(([key]) => errors[key]);
    first?.[1].current?.focus();
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;
    setFormError("");

    const errors = validate({ fullName, email, password, confirmPassword });
    setFieldErrors(errors);
    if (Object.keys(errors).length) {
      focusFirstInvalid(errors);
      return;
    }

    setIsSubmitting(true);
    try {
      await signup(fullName.trim(), email.trim(), password);
      navigate("/home", { replace: true });
    } catch (err) {
      // Show the server's own explanation next to the field it is about, when it names one.
      const serverFields = {};
      if (err.fieldErrors?.name) serverFields.name = err.fieldErrors.name;
      if (err.fieldErrors?.email) serverFields.email = err.fieldErrors.email;
      if (err.fieldErrors?.password) serverFields.password = err.fieldErrors.password;
      if (err.status === 409) serverFields.email = err.message;
      if (Object.keys(serverFields).length) {
        setFieldErrors(serverFields);
        focusFirstInvalid(serverFields);
      } else {
        setFormError(err.message || "Something went wrong. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth">
      <AuthPanel heading="Start planning together." text="Create an account to discover destinations and plan trips with your group." />

      <div className="auth__form-side">
        <div className="auth-card">
          <h1>Create your account</h1>
          <p className="auth-card__subtext">Join TravelSync and plan your next trip.</p>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div className="form-field">
              <label htmlFor="fullName">Full Name</label>
              <input id="fullName" ref={nameRef} type="text" autoComplete="name" value={fullName} maxLength={80}
                onChange={(e) => setFullName(e.target.value)} placeholder="Your full name"
                aria-invalid={Boolean(fieldErrors.name) || undefined} aria-describedby={fieldErrors.name ? "name-error" : undefined} />
              {fieldErrors.name && <p className="field-error" id="name-error" role="alert">{fieldErrors.name}</p>}
            </div>

            <div className="form-field">
              <label htmlFor="email">Email</label>
              <input id="email" ref={emailRef} type="email" autoComplete="email" value={email} maxLength={254}
                onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com"
                aria-invalid={Boolean(fieldErrors.email) || undefined} aria-describedby={fieldErrors.email ? "email-error" : undefined} />
              {fieldErrors.email && <p className="field-error" id="email-error" role="alert">{fieldErrors.email}</p>}
            </div>

            <div className="form-field">
              <PasswordInput id="password" label="Password" value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="Create a password" autoComplete="new-password" inputRef={passwordRef}
                describedBy={`password-requirements${fieldErrors.password ? " password-error" : ""}`} invalid={Boolean(fieldErrors.password)} />
              <PasswordRequirements id="password-requirements" password={password} />
              {fieldErrors.password && <p className="field-error" id="password-error" role="alert">{fieldErrors.password}</p>}
            </div>

            <div className="form-field">
              <PasswordInput id="confirmPassword" label="Confirm Password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter your password" autoComplete="new-password" inputRef={confirmRef}
                describedBy={liveConfirmError || fieldErrors.confirmPassword ? "confirm-error" : undefined}
                invalid={Boolean(liveConfirmError || fieldErrors.confirmPassword)} />
              {(liveConfirmError || fieldErrors.confirmPassword) && (
                <p className="field-error" id="confirm-error" role="alert">{liveConfirmError || fieldErrors.confirmPassword}</p>
              )}
            </div>

            {formError && <p className="auth-form__error" role="alert">{formError}</p>}

            <button type="submit" className="btn btn--primary auth-form__submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating account..." : "Create Account"}
            </button>
          </form>

          <p className="auth-card__footer">Already have an account? <Link to="/login">Log In</Link></p>
        </div>
      </div>
    </div>
  );
}
