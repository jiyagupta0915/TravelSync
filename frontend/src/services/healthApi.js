const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function getTravelHealth(destination, month) {
  const params = month ? `?month=${month}` : "";
  const response = await fetch(
    `${API_BASE_URL}/api/travel-health/${encodeURIComponent(destination)}${params}`,
    { credentials: "include" }
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Could not load travel health information.");
  return data;
}
