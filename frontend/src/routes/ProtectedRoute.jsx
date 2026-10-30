// Guards every private page.
//   loading         -> a loading screen (no flash-redirect to /login)
//   error           -> "can't reach TravelSync" with Retry (the session may still be valid)
//   unauthenticated -> redirect to /login, remembering where the user was going
// Works both wrapping children and as a layout route (renders <Outlet/> when it has no children).

import { Navigate, Outlet, useLocation } from "react-router-dom";
import StatusScreen from "../components/StatusScreen/StatusScreen";
import { useAuth } from "../context/useAuth";

export default function ProtectedRoute({ children }) {
  const { status, error, retry } = useAuth();
  const location = useLocation();

  if (status === "loading") return <StatusScreen kind="loading" message="Checking your session…" />;

  if (status === "error") {
    const offline = error?.kind === "network";
    return (
      <StatusScreen
        kind="error"
        title={offline ? "Can't reach TravelSync" : "TravelSync is having trouble"}
        message={error?.message || "Please try again in a moment."}
        onRetry={retry}
      />
    );
  }

  if (status !== "authenticated") {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }

  return children ?? <Outlet />;
}
