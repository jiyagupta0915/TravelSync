import { useCallback, useSyncExternalStore } from "react";

// Subscribes to a CSS media query. Falls back to `fallback` where matchMedia doesn't exist (e.g. SSR/tests).
export function useMediaQuery(query, fallback = true) {
  const subscribe = useCallback((onChange) => {
    if (typeof window === "undefined" || !window.matchMedia) return () => {};
    const list = window.matchMedia(query);
    list.addEventListener("change", onChange);
    return () => list.removeEventListener("change", onChange);
  }, [query]);

  const getSnapshot = useCallback(() => (
    typeof window !== "undefined" && window.matchMedia ? window.matchMedia(query).matches : fallback
  ), [query, fallback]);

  return useSyncExternalStore(subscribe, getSnapshot, () => fallback);
}
