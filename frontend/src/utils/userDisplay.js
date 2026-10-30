// Never render "undefined": every value falls back to something sensible.
export function getDisplayName(user) {
  const name = typeof user?.name === "string" ? user.name.trim() : "";
  if (name) return name;
  const email = typeof user?.email === "string" ? user.email.trim() : "";
  return email ? email.split("@")[0] : "Traveller";
}

export function getFirstName(user) {
  return getDisplayName(user).split(" ")[0];
}

export function getInitials(user) {
  const parts = getDisplayName(user).split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : parts[0]?.slice(0, 2) || "";
  return (letters || "?").toUpperCase();
}
