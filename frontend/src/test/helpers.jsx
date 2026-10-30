import { MemoryRouter } from "react-router-dom";
import { AuthContext } from "../context/authContext";

// Pretend the viewport is `width` px wide (desktop shell breakpoint is 901px).
export function setViewport(width) {
  window.matchMedia = (query) => {
    const min = /min-width:\s*(\d+)px/.exec(query);
    const matches = min ? width >= Number(min[1]) : false;
    return { matches, media: query, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} };
  };
}

export const TEST_USER = { id: "u1", name: "Asha Rao", email: "asha@example.com", settings: {} };

export function authValue(overrides = {}) {
  return {
    status: "authenticated", user: TEST_USER, error: null, isAuthenticated: true, isLoading: false,
    login: async () => TEST_USER, signup: async () => TEST_USER, logout: async () => true, retry: () => {}, updateUser: () => {},
    ...overrides,
  };
}

export function renderWithProviders(ui, { route = "/", auth = {} } = {}) {
  return (
    <AuthContext.Provider value={authValue(auth)}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </AuthContext.Provider>
  );
}
