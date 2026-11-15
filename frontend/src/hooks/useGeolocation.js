import { useCallback, useState } from "react";

function messageFor(error) {
  if (error?.code === 1) return "Location permission was denied. You can allow it in your browser's site settings and try again.";
  if (error?.code === 3) return "Finding your location took too long. Please try again.";
  return "Your location couldn't be determined right now.";
}

// Asks the browser for the user's position, but ONLY when locate() is called (from a button press), never on page load.
//   status   "idle" | "locating" | "located" | "error"
//   position { lat, lon } once located
export function useGeolocation() {
  const [state, setState] = useState({ status: "idle", position: null, error: "" });

  const locate = useCallback(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setState({ status: "error", position: null, error: "Your browser doesn't support location." });
      return;
    }
    setState((previous) => ({ ...previous, status: "locating", error: "" }));
    navigator.geolocation.getCurrentPosition(
      (result) => setState({ status: "located", position: { lat: result.coords.latitude, lon: result.coords.longitude }, error: "" }),
      (error) => setState({ status: "error", position: null, error: messageFor(error) }),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 5 * 60 * 1000 },
    );
  }, []);

  const clear = useCallback(() => setState({ status: "idle", position: null, error: "" }), []);

  return { ...state, locate, clear };
}