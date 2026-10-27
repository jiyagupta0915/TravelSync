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