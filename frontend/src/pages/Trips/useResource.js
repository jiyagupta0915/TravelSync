import { useEffect, useRef, useState } from "react";

// Loads one piece of data and keeps loading / error / data separate, so one slow or failing
// section never blocks the others. `key` says what the data is for (a trip id, a destination...).
export function useResource(key, loader, enabled = true) {
  const [state, setState] = useState({ key: null, data: null, error: "" });
  const loaderRef = useRef(loader);
  useEffect(() => { loaderRef.current = loader; });   // runs before the fetch effect below

  useEffect(() => {
    if (!enabled) return undefined;
    let active = true;
    loaderRef.current()
      .then((data) => active && setState({ key, data, error: "" }))
      .catch((err) => active && setState({ key, data: null, error: err.message }));
    return () => { active = false; };
  }, [key, enabled]);

  const ready = enabled && state.key === key;
  return {
    loading: enabled && !ready,
    data: ready ? state.data : null,
    error: ready ? state.error : "",
    update: (updater) => setState((prev) => (prev.key === key ? { ...prev, data: updater(prev.data) } : prev)),
  };
}