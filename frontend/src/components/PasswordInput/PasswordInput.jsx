import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import "./PasswordInput.css";

// Reusable password field with a show/hide toggle.
// Used on both Login and Signup so the behavior stays consistent.
export default function PasswordInput({ id, label, value, onChange, placeholder }) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div className="password-input">
      <label htmlFor={id} className="password-input__label">
        {label}
      </label>
      <div className="password-input__field">
        <input
          id={id}
          type={isVisible ? "text" : "password"}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required
          className="password-input__control"
        />
        <button
          type="button"
          className="password-input__toggle"
          onClick={() => setIsVisible((visible) => !visible)}
          aria-label={isVisible ? "Hide password" : "Show password"}
        >
          {isVisible ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
    </div>
  );
}