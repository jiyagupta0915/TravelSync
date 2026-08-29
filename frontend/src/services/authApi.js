// TEMPORARY FRONTEND MOCK AUTH
// This file simulates what real FastAPI auth endpoints will return.
// Replace the internals of these functions with real fetch() calls
// once the backend exists — AuthContext and every component that
// consumes it will not need to change.

const SESSION_KEY = "travelsync_mock_user";
const USERS_KEY = "travelsync_mock_users"; // simulates a users table

const fakeDelay = (ms = 600) => new Promise((resolve) => setTimeout(resolve, ms));

function getAllUsers() {
  const raw = localStorage.getItem(USERS_KEY);
  return raw ? JSON.parse(raw) : {};
}

function saveAllUsers(users) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

/**
 * Mock login.
 * Looks up the email in the mock "users table" so the name entered
 * at signup is remembered. In production this will POST /auth/login.
 */
export async function mockLogin(email, password) {
  await fakeDelay();

  if (!email || !password) {
    throw new Error("Email and password are required.");
  }

  const users = getAllUsers();
  const existingUser = users[email];

  // Falls back to deriving a name from the email only if this
  // email was never used to sign up in this browser before.
  const name = existingUser
    ? existingUser.name
    : email.split("@")[0].charAt(0).toUpperCase() + email.split("@")[0].slice(1);

  const user = existingUser || {
    id: crypto.randomUUID(),
    name,
    email,
  };

  // Register it if it didn't already exist, so future logins remember it.
  if (!existingUser) {
    users[email] = user;
    saveAllUsers(users);
  }

  localStorage.setItem(SESSION_KEY, JSON.stringify(user));
  return user;
}

/**
 * Mock signup.
 * Registers the user in the mock "users table" and starts a session.
 * In production this will POST /auth/signup.
 */
export async function mockSignup(fullName, email, password) {
  await fakeDelay();

  if (!fullName || !email || !password) {
    throw new Error("All fields are required.");
  }

  const user = {
    id: crypto.randomUUID(),
    name: fullName.trim(),
    email,
  };

  const users = getAllUsers();
  users[email] = user;
  saveAllUsers(users);

  localStorage.setItem(SESSION_KEY, JSON.stringify(user));
  return user;
}

/**
 * Mock logout — clears only the active session, not the users table.
 */
export function mockLogout() {
  localStorage.removeItem(SESSION_KEY);
}

/**
 * Reads any existing mock session from localStorage.
 * Used on app load so refreshing the page doesn't log the user out.
 */
export function getStoredUser() {
  const raw = localStorage.getItem(SESSION_KEY);
  return raw ? JSON.parse(raw) : null;
}