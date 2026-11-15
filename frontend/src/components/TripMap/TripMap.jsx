import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./TripMap.css";

// Map tiles are © OpenStreetMap contributors. The public OSM tile server is fine for a project like this,
// but it is not meant for heavy traffic: before a real launch, switch to a hosted tile provider (Geoapify,
// MapTiler, Stadia...) by changing only the two constants below.
const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors';

function pinIcon(marker, selected) {
  const size = marker.kind === "place" ? 34 : 30;
  return L.divIcon({
    className: "",                       // drop Leaflet's default white box
    html: `<span class="tmap-pin tmap-pin--${marker.kind}${selected ? " is-selected" : ""}">${marker.symbol}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

// Popup content is built with DOM nodes + textContent, never HTML strings: place and stay names come from
// OpenStreetMap, so they must never be able to inject markup.
function popupNode(marker) {
  const root = document.createElement("div");
  root.className = "tmap-popup";
  const title = document.createElement("strong");
  title.textContent = marker.title;
  root.appendChild(title);
  for (const line of marker.lines || []) {
    const p = document.createElement("p");
    p.textContent = line;
    root.appendChild(p);
  }
  for (const link of marker.links || []) {
    if (!/^https?:\/\//i.test(link.href || "")) continue;          // only ever link to web addresses
    const a = document.createElement("a");
    a.href = link.href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = link.label;
    root.appendChild(a);
  }
  return root;
}

// A thin wrapper around Leaflet. It owns the map; the page above owns the data.
//   markers    [{ id, kind, symbol, lat, lon, title, lines[], links[] }]
//   selectedId highlighted marker (its popup opens and the map pans to it)
//   onSelect   called with a marker id when the user clicks a pin
//   emptyZoom  zoom level used when there are no pins at all (5 shows all of India)
export default function TripMap({ center, markers, selectedId, onSelect, emptyZoom = 11 }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const markerRefs = useRef(new Map());
  const onSelectRef = useRef(onSelect);
  const fittedFor = useRef("");

  useEffect(() => { onSelectRef.current = onSelect; });

  // Create the map once.
  useEffect(() => {
    const map = L.map(containerRef.current, { scrollWheelZoom: false, zoomControl: false }).setView([center.lat, center.lon], 11);
    L.control.zoom({ position: "bottomleft" }).addTo(map);   // bottom-left, so popups never open underneath it
    L.tileLayer(TILE_URL, { attribution: TILE_ATTRIBUTION, maxZoom: 19 }).addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    const refs = markerRefs.current;
    // Scroll-to-zoom only after the map is clicked, so scrolling the page never gets "stuck" on the map.
    map.on("click focus", () => map.scrollWheelZoom.enable());
    map.on("blur mouseout", () => map.scrollWheelZoom.disable());
    // The map can start inside a panel that is still animating or resized later: keep Leaflet's size in sync.
    const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => map.invalidateSize()) : null;
    observer?.observe(containerRef.current);
    return () => { observer?.disconnect(); map.remove(); mapRef.current = null; layerRef.current = null; refs.clear(); fittedFor.current = ""; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Rebuild the pins whenever the list of markers changes.
  useEffect(() => {
    const map = mapRef.current;
    const layer = layerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();
    markerRefs.current.clear();
    for (const m of markers) {
      const pin = L.marker([m.lat, m.lon], { icon: pinIcon(m, false), keyboard: true, title: m.title, riseOnHover: true });
      pin.bindPopup(() => popupNode(m), { maxWidth: 260, closeButton: true });
      pin.on("click", () => onSelectRef.current?.(m.id));
      pin.addTo(layer);
      markerRefs.current.set(m.id, { pin, marker: m });
    }
    // Zoom to fit all pins, but only when the SET of pins changed (not on every selection).
    const signature = markers.map((m) => m.id).sort().join("|");
    if (signature !== fittedFor.current) {
      fittedFor.current = signature;
      if (markers.length > 1) map.fitBounds(L.latLngBounds(markers.map((m) => [m.lat, m.lon])), { padding: [40, 40], maxZoom: 15 });
      else if (markers.length === 1) map.setView([markers[0].lat, markers[0].lon], 14);
      else map.setView([center.lat, center.lon], emptyZoom);
    }
  }, [markers, center.lat, center.lon, emptyZoom]);

  // Highlight and open the selected pin.
  useEffect(() => {
    const map = mapRef.current;
    for (const [id, { pin, marker }] of markerRefs.current) pin.setIcon(pinIcon(marker, id === selectedId));
    const chosen = markerRefs.current.get(selectedId);
    if (map && chosen) {
      map.panTo(chosen.pin.getLatLng(), { animate: true });
      chosen.pin.openPopup();
    } else if (map) {
      map.closePopup();
    }
  }, [selectedId, markers]);

  return <div ref={containerRef} className="tmap" role="region" aria-label="Interactive trip map" />;
}