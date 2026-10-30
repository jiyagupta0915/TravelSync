import { sanitizeInteger } from "../../utils/numberField";
import "./NumberField.css";

// A whole-number text field for amounts like budget (₹) and distance (km).
//  * Typed by hand on any keyboard (inputMode="numeric" shows the number pad on phones).
//  * It is a text input on purpose, so browsers draw no increment/decrement spinner.
//  * The value is the raw string: an empty field stays empty while the user types and is never turned into 0.
//    Converting to a number (and validating it) happens on submit, see utils/numberField.js.
//  * Pasted "20,000" or "₹ 20000.50" is cleaned to digits.
export default function NumberField({ id, value, onChange, inputRef, invalid = false, describedBy, maxLength = 9, placeholder, ariaLabel, className = "" }) {
  return (
    <input
      id={id}
      ref={inputRef}
      className={`number-field ${className}`.trim()}
      type="text"
      inputMode="numeric"
      autoComplete="off"
      maxLength={maxLength + 6}
      placeholder={placeholder}
      aria-label={ariaLabel}
      aria-invalid={invalid || undefined}
      aria-describedby={describedBy}
      value={value}
      onChange={(event) => onChange(sanitizeInteger(event.target.value).slice(0, maxLength))}
    />
  );
}
