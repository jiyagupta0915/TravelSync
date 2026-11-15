import { formatDuration, formatKm, haversineKm } from "../../utils/geo";

function inr(value) {
  return `₹${Number(value).toLocaleString("en-IN")}`;
}

// "By road" comes from the server (Geoapify). Without it, but with the user's location, we show the free
// straight-line distance instead, clearly labelled as approximate.
function distanceOf(id, point, position, drive) {
  if (drive?.[id]) return `By road: ${formatKm(drive[id].km)} · about ${formatDuration(drive[id].minutes)}`;
  if (position) return `Straight line: about ${formatKm(haversineKm(position, point))}`;
  return "";
}

function stayLines(stay) {
  return [
    `${stay.type_label || "Stay"}${stay.stars ? ` · ${stay.stars}★` : ""}`,
    stay.address,
    stay.price_low_inr ? `${inr(stay.price_low_inr)}–${inr(stay.price_high_inr)} per ${stay.price_unit} (estimate)` : "",
  ].filter(Boolean);
}

function stayMarker(stay, kind, position, drive) {
  const id = `${kind === "stay" ? "stay" : "suggested"}:${stay.key}`;
  const distance = distanceOf(`stay:${stay.key}`, stay, position, kind === "stay" ? drive : null);
  return {
    id,
    kind,
    symbol: kind === "stay" ? "★" : "•",
    lat: stay.lat,
    lon: stay.lon,
    title: stay.name,
    sub: `${stay.type_label || "Stay"}${stay.stars ? ` · ${stay.stars}★` : ""}`,
    distance,
    lines: [...stayLines(stay), distance].filter(Boolean),
    links: [
      stay.website ? { label: "Website", href: stay.website } : null,
      stay.maps_url ? { label: "Open in Maps", href: stay.maps_url } : null,
    ].filter(Boolean),
  };
}

function placeMarker(place, position, drive) {
  const distance = distanceOf(`place:${place.rank}`, place, position, drive);
  return {
    id: `place:${place.rank}`,
    kind: "place",
    symbol: String(place.rank),
    lat: place.lat,
    lon: place.lon,
    title: place.name,
    sub: place.category,
    distance,
    lines: [
      [place.category, place.rating ? `${place.rating}★` : "", place.duration_hrs ? `about ${place.duration_hrs} h` : ""].filter(Boolean).join(" · "),
      place.description,
      distance,
    ].filter(Boolean),
    links: [{ label: "Directions", href: `https://www.google.com/maps/dir/?api=1&destination=${place.lat},${place.lon}` }],
  };
}

// Builds every pin for the map, in list order: you, the destination, top places, shortlisted stays, suggested stays.
//   data       the /map response (or null when there is no trip)
//   suggested  array of live stay suggestions, or null when that layer is off
//   position   { lat, lon } of the user, or null
//   drive      { [id]: { km, minutes } } driving data from the server, or null
export function buildMarkers({ data, showPlaces, showSaved, suggested, position, drive }) {
  const markers = [];
  const unlocated = [];

  if (position) {
    markers.push({
      id: "me", kind: "me", symbol: "●", lat: position.lat, lon: position.lon,
      title: "You are here", sub: "Your approximate location", distance: "",
      lines: ["Your approximate location, from your browser."], links: [],
    });
  }

  if (data) {
    const center = { lat: data.center.lat, lon: data.center.lon };
    const distance = distanceOf("destination", center, position, drive);
    markers.push({
      id: "destination", kind: "dest", symbol: "⚑", lat: center.lat, lon: center.lon,
      title: data.destination, sub: "Destination", distance,
      lines: ["Destination (town centre)", distance].filter(Boolean), links: [],
    });

    if (showPlaces) {
      for (const place of data.places) {
        if (place.lat === null || place.lon === null) unlocated.push(place.name);
        else markers.push(placeMarker(place, position, drive));
      }
    }
    if (showSaved) for (const stay of data.saved_stays) markers.push(stayMarker(stay, "stay", position, drive));
    if (suggested) {
      const savedKeys = new Set(data.saved_stays.map((s) => s.key));
      suggested.filter((s) => !savedKeys.has(s.key)).slice(0, 10).forEach((s) => markers.push(stayMarker(s, "suggested", position, null)));
    }
  }
  return { markers, unlocated };
}