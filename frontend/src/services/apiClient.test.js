import { afterEach, describe, expect, it, vi } from "vitest";
import { apiRequest, ApiError, parseErrorBody, setUnauthorizedListener } from "./apiClient";

function mockFetch(status, body, { raw } = {}) {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: status < 400, status, text: async () => (raw ?? JSON.stringify(body)) })));
}

afterEach(() => { vi.unstubAllGlobals(); setUnauthorizedListener(null); });

describe("parseErrorBody understands every backend error shape", () => {
  it("our {error, code, details}", () => {
    const r = parseErrorBody({ error: "password: too weak", code: "validation_error", details: [{ field: "password", message: "too weak" }] }, 422);
    expect(r.message).toBe("password: too weak");
    expect(r.fieldErrors).toEqual({ password: "too weak" });
  });
  it("FastAPI {detail: string}", () => {
    expect(parseErrorBody({ detail: "Not Found" }, 404).message).toBe("Not Found");
  });
  it("FastAPI {detail: [{loc, msg}]}", () => {
    const r = parseErrorBody({ detail: [{ loc: ["body", "email"], msg: "Value error, Enter a valid email address." }] }, 422);
    expect(r.fieldErrors.email).toBe("Enter a valid email address.");
    expect(r.message).toBe("email: Enter a valid email address.");
  });
  it("falls back to friendly text per status when the body is useless", () => {
    expect(parseErrorBody(null, 500).message).toMatch(/server/i);
    expect(parseErrorBody(null, 401).message).toMatch(/session/i);
    expect(parseErrorBody(null, 403).message).toMatch(/permission/i);
    expect(parseErrorBody(null, 429).message).toMatch(/too many/i);
  });
});

describe("apiRequest", () => {
  it("always sends credentials and never touches localStorage for tokens", async () => {
    mockFetch(200, { ok: true });
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    await apiRequest("/api/x");
    expect(fetch.mock.calls[0][1].credentials).toBe("include");
    expect(setItem).not.toHaveBeenCalled();
  });

  it.each([[401, "unauthorized"], [403, "forbidden"], [404, "notfound"], [422, "validation"], [429, "ratelimit"], [503, "server"]])(
    "classifies %i as %s", async (status, kind) => {
      mockFetch(status, { error: "x" });
      await expect(apiRequest("/api/x", { skipUnauthorizedHandler: true })).rejects.toMatchObject({ kind, status });
    });

  it("reports a network failure as kind 'network' (not as logged out)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    const err = await apiRequest("/api/x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe("network");
    expect(err.message).toMatch(/can't reach/i);
  });

  it("survives a non-JSON error page from a proxy", async () => {
    mockFetch(502, null, { raw: "<html>Bad gateway</html>" });
    const err = await apiRequest("/api/x").catch((e) => e);
    expect(err.kind).toBe("server");
    expect(err.message).not.toMatch(/html/i);
  });

  it("notifies the app on 401 except where the caller opts out", async () => {
    const listener = vi.fn();
    setUnauthorizedListener(listener);
    mockFetch(401, { error: "You must be logged in to continue." });
    await apiRequest("/api/trips").catch(() => {});
    expect(listener).toHaveBeenCalledTimes(1);
    await apiRequest("/api/auth/login", { skipUnauthorizedHandler: true }).catch(() => {});
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
