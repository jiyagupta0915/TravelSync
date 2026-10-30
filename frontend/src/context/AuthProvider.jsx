import { useCallback, useEffect, useMemo, useState } from "react";
import { AuthContext } from "./authContext";
import { getCurrentUser, login as apiLogin, logout as apiLogout, signup as apiSignup } from "../services/authApi";
import { isAbort, setUnauthorizedListener } from "../services/apiClient";

// status is one of:
//   "loading"          - asking the server whether there is a session
//   "authenticated"    - a valid session; `user` is set
//   "unauthenticated"  - the server said there is no (valid) session
//   "error"            - the server could not be reached / failed. This is NOT "logged out": the session may be fine,
//                        so we offer a retry instead of throwing the user to the login page.
// The session itself lives in an httpOnly cookie; nothing sensitive is ever stored in JavaScript or localStorage.
const LOADING = { status: "loading", user: null, error: null };
const SIGNED_OUT = { status: "unauthenticated", user: null, error: null };

export function AuthProvider({ children }) {
  const [state, setState] = useState(LOADING);

  const refresh = useCallback(async () => {
    try {
      const user = await getCurrentUser();
      setState(user ? { status: "authenticated", user, error: null } : SIGNED_OUT);
    } catch (error) {
      if (isAbort(error)) return;
      setState((previous) => ({ status: "error", user: previous.user, error }));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // A 401 from any authenticated request means the session ended (expired, revoked, signed out elsewhere).
  useEffect(() => {
    setUnauthorizedListener(() => {
      setState((previous) => (previous.status === "authenticated" ? SIGNED_OUT : previous));
    });
    return () => setUnauthorizedListener(null);
  }, []);

  const retry = useCallback(() => {
    setState(LOADING);
    return refresh();
  }, [refresh]);

  const login = useCallback(async (email, password) => {
    const user = await apiLogin(email, password);
    setState({ status: "authenticated", user, error: null });
    return user;
  }, []);

  const signup = useCallback(async (fullName, email, password) => {
    // The backend creates the account and the session in one request.
    const user = await apiSignup(fullName, email, password);
    setState({ status: "authenticated", user, error: null });
    return user;
  }, []);

  const logout = useCallback(async () => {
    let serverConfirmed = true;
    try {
      await apiLogout();
    } catch {
      serverConfirmed = false;      // the cookie could not be cleared server-side; we still leave the signed-in UI
    } finally {
      setState(SIGNED_OUT);
    }
    return serverConfirmed;
  }, []);

  const updateUser = useCallback((changes) => {
    setState((previous) => (previous.user ? { ...previous, user: { ...previous.user, ...changes } } : previous));
  }, []);

  const value = useMemo(() => ({
    status: state.status,
    user: state.user,
    error: state.error,
    isAuthenticated: state.status === "authenticated",
    isLoading: state.status === "loading",
    login, signup, logout, retry, updateUser,
  }), [state, login, signup, logout, retry, updateUser]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
