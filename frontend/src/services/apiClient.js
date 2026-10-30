// The one place that talks to the backend. Every service module uses `apiRequest`.
//
//  * Always sends the httpOnly auth cookie (credentials: "include"); no token is ever kept in JS or localStorage.
//  * Understands every error body the backend can produce: {error, code, details[]}, FastAPI's {detail: "..."} and
//    {detail: [{loc, msg}]}, plain text / HTML from a proxy, and network failures.
//  * Throws ApiError with a `kind` so callers can tell the situations apart:
//      "network" (never reached the server), "unauthorized" (401), "forbidden" (403), "notfound" (404),
//      "validation" (400/422 or other 4xx), "ratelimit" (429), "server" (5xx).

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(message, { status = 0, kind = "server", code = null, fieldErrors = {}, details = [] } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.kind = kind;
    this.code = code;
    this.fieldErrors = fieldErrors;
    this.details = details;
  }
}

function kindForStatus(status) {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "notfound";
  if (status === 429) return "ratelimit";
  if (status >= 500) return "server";
  return "validation";
}

function fieldName(loc) {
  if (!Array.isArray(loc)) return "";
  return loc.filter((part) => !["body", "query", "path"].includes(part)).join(".");
}

export function parseErrorBody(data, status, fallback) {
  let message = "";
  let details = [];
  let code = null;

  if (data && typeof data === "object") {
    code = typeof data.code === "string" ? data.code : null;
    if (typeof data.error === "string") message = data.error;
    if (Array.isArray(data.details)) {
      details = data.details.filter((d) => d && typeof d.message === "string");
    }
    if (!message && typeof data.detail === "string") message = data.detail;
    if (!message && Array.isArray(data.detail)) {
      details = data.detail.map((d) => ({ field: fieldName(d.loc), message: String(d.msg || "Invalid value.").replace(/^Value error, /, "") }));
      const first = details[0];
      message = first ? (first.field ? `${first.field}: ${first.message}` : first.message) : "";
    }
    if (!message && typeof data.message === "string") message = data.message;
  }

  if (!message) {
    if (status === 401) message = "Your session has expired. Please log in again.";
    else if (status === 403) message = "You don't have permission to do that.";
    else if (status === 404) message = "That could not be found.";
    else if (status === 429) message = "Too many attempts. Please wait a moment and try again.";
    else if (status >= 500) message = "The server ran into a problem. Please try again in a moment.";
    else message = fallback || "The request could not be completed.";
  }

  const fieldErrors = {};
  for (const d of details) {
    if (d.field && !fieldErrors[d.field]) fieldErrors[d.field] = d.message;
  }
  return { message, details, fieldErrors, code };
}

// Called when an authenticated request comes back 401, so the app can show the login screen
// instead of leaving the user on a page that can no longer load anything.
let unauthorizedListener = null;
export function setUnauthorizedListener(listener) {
  unauthorizedListener = listener;
}

export async function apiRequest(path, { method = "GET", body, signal, fallbackMessage, skipUnauthorizedHandler = false } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      credentials: "include",
      headers: body !== undefined ? { "Content-Type": "application/json", Accept: "application/json" } : { Accept: "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new ApiError("Can't reach TravelSync. Check your internet connection and try again.", { kind: "network" });
  }

  let data = null;
  const text = await response.text().catch(() => "");
  if (text) {
    try { data = JSON.parse(text); } catch { data = null; }
  }

  if (!response.ok) {
    const { message, details, fieldErrors, code } = parseErrorBody(data, response.status, fallbackMessage);
    const error = new ApiError(message, { status: response.status, kind: kindForStatus(response.status), code, details, fieldErrors });
    if (error.kind === "unauthorized" && !skipUnauthorizedHandler && unauthorizedListener) unauthorizedListener(error);
    throw error;
  }
  return data ?? {};
}

export function isAbort(error) {
  return error?.name === "AbortError";
}
