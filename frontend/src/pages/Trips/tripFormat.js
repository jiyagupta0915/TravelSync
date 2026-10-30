export function formatDate(value, withYear = true) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", ...(withYear ? { year: "numeric" } : {}) }).format(date);
}

export function formatTripDates(trip) {
  if (trip.start_date && trip.end_date) return `${formatDate(trip.start_date, false)} – ${formatDate(trip.end_date)}`;
  return "Dates not set";
}

export function todayIso() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

// A trip is "previous" once its end date (set in the Packing assistant) is in the past. Trips without dates can't
// be classified, so they stay under Upcoming rather than being guessed.
export function isPreviousTrip(trip, today = todayIso()) {
  return Boolean(trip.end_date) && trip.end_date < today;
}
