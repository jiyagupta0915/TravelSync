import { Check, Circle } from "lucide-react";
import { checkPassword, PASSWORD_MAX_BYTES } from "../../utils/passwordPolicy";
import "./PasswordRequirements.css";

// Live checklist for a NEW password. Each row says "met" / "not met" in text too, not only through colour/icon.
export default function PasswordRequirements({ id, password }) {
  const { results, tooLong } = checkPassword(password);
  return (
    <div className="pw-req" id={id}>
      <p className="pw-req__title">Your password needs:</p>
      <ul>
        {results.map((rule) => (
          <li key={rule.id} className={rule.met ? "is-met" : ""}>
            {rule.met ? <Check size={14} aria-hidden="true" /> : <Circle size={14} aria-hidden="true" />}
            <span>{rule.label}</span>
            <span className="sr-only">{rule.met ? " — met" : " — not met yet"}</span>
          </li>
        ))}
      </ul>
      {tooLong && <p className="pw-req__warn" role="alert">Use at most {PASSWORD_MAX_BYTES} bytes (about 72 characters).</p>}
    </div>
  );
}
