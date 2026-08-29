const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Authentication request failed.");
  return data;
}

export async function login(email, password) {
  const data = await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return data.user;
}

export async function signup(name, email, password) {
  const data = await request("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
  return data.user;
}

export async function logout() {
  await request("/api/auth/logout", { method: "POST" });
}

export async function getCurrentUser() {
  const data = await request("/api/auth/me");
  return data.user;
}
