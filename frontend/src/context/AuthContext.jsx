// TEMPORARY FRONTEND MOCK AUTH
// This context stands in for real FastAPI/JWT authentication.
// Every page reads auth state from here rather than managing its
// own copy, so swapping in the real backend later only requires
// changing authApi.js — not the pages/components themselves.

import { createContext, useContext, useEffect, useState } from "react";
import { mockLogin, mockSignup, mockLogout, getStoredUser } from "../services/authApi";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // On first load, check if a mock session already exists
  // (e.g. the user refreshed the page).
  useEffect(() => {
    const storedUser = getStoredUser();
    if (storedUser) {
      setUser(storedUser);
    }
    setIsLoading(false);
  }, []);

  async function login(email, password) {
    const loggedInUser = await mockLogin(email, password);
    setUser(loggedInUser);
    return loggedInUser;
  }

  async function signup(fullName, email, password) {
    const newUser = await mockSignup(fullName, email, password);
    setUser(newUser);
    return newUser;
  }

  function logout() {
    mockLogout();
    setUser(null);
  }

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    signup,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook so components just call useAuth() instead of
// importing useContext + AuthContext everywhere.
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}