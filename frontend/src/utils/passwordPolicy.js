// Mirrors backend/app/core/password_policy.py exactly. Applies to NEW passwords only
// (signup, change, reset). It must never be applied to the login form.

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_BYTES = 72;

export const PASSWORD_RULES = [
  { id: "length", label: "At least 8 characters", test: (pw) => pw.length >= PASSWORD_MIN_LENGTH },
  { id: "upper", label: "One uppercase letter (A–Z)", test: (pw) => /[A-Z]/.test(pw) },
  { id: "lower", label: "One lowercase letter (a–z)", test: (pw) => /[a-z]/.test(pw) },
  { id: "number", label: "One number (0–9)", test: (pw) => /[0-9]/.test(pw) },
  { id: "special", label: "One special character (e.g. ! @ # $ %)", test: (pw) => /[^A-Za-z0-9\s]/.test(pw) },
];

export function passwordByteLength(password) {
  return new TextEncoder().encode(password).length;
}

export function checkPassword(password) {
  const results = PASSWORD_RULES.map((rule) => ({ id: rule.id, label: rule.label, met: rule.test(password) }));
  const tooLong = passwordByteLength(password) > PASSWORD_MAX_BYTES;
  return { results, tooLong, valid: results.every((r) => r.met) && !tooLong };
}
