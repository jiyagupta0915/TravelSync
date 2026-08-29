// Wraps any private page. If the user is not authenticated, they are
// redirected to /login instead of seeing the protected content.
// Once real FastAPI/JWT auth exists, only useAuth()'s internals change —
// this component stays the same.

import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  // Avoid a flash-redirect to /login while we're still checking
  // localStorage for an existing mock session on first load.
  if (isLoading) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}