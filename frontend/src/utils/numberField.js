// Helpers for numeric text inputs. The field state is always the raw string the user typed, so an empty
// field stays empty while typing (it is never silently turned into 0). Conversion happens only on submit.

// "20,000" -> "20000"; "20000.75" -> "20000" (amounts here are whole numbers); anything else non-numeric is dropped.
export function sanitizeInteger(raw) {
  const text = String(raw).replace(/[,\s₹]/g, "");
  const wholePart = text.split(".")[0];
  return wholePart.replace(/[^\d]/g, "");
}

export function parsePositiveInteger(raw, { label, min = 1, max, unit = "" }) {
  const text = String(raw ?? "").trim();
  if (text === "") return { ok: false, error: `Enter ${label}.` };
  if (!/^\d+$/.test(text)) return { ok: false, error: `${capitalise(label)} must be a whole number.` };
  const value = Number(text);
  if (!Number.isSafeInteger(value)) return { ok: false, error: `${capitalise(label)} is too large.` };
  if (value < min) return { ok: false, error: `${capitalise(label)} must be at least ${format(min)}${unit}.` };
  if (max !== undefined && value > max) return { ok: false, error: `${capitalise(label)} can't be more than ${format(max)}${unit}.` };
  return { ok: true, value };
}

function capitalise(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function format(n) {
  return Number(n).toLocaleString("en-IN");
}
