import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import "./PasswordInput.css";

// Reusable password field with a show/hide toggle, used by Login, Signup, Reset and Change-password.
export default function PasswordInput({
  id, label, value, onChange, placeholder, autoComplete = "current-password", describedBy, invalid = false, inputRef, maxLength,
}) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div className="password-input">
      <label htmlFor={id} className="password-input__label">{label}</label>
      <div className="password-input__field">
        <input
          id={id}
          ref={inputRef}
          type={isVisible ? "text" : "password"}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete={autoComplete}
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
          maxLength={maxLength}
          className="password-input__control"
        />
        <button
          type="button"
          className="password-input__toggle"
          onClick={() => setIsVisible((visible) => !visible)}
          aria-label={isVisible ? "Hide password" : "Show password"}
          aria-pressed={isVisible}
        >
          {isVisible ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
    </div>
  );
}
