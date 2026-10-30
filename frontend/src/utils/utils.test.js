import { describe, expect, it } from "vitest";
import { checkPassword, PASSWORD_RULES } from "./passwordPolicy";
import { parsePositiveInteger, sanitizeInteger } from "./numberField";
import { getDisplayName, getFirstName, getInitials } from "./userDisplay";

describe("password policy (must mirror the backend)", () => {
  it("accepts a password meeting every rule", () => {
    expect(checkPassword("Str0ng!Passw0rd").valid).toBe(true);
  });

  it.each([
    ["Sh0rt!a", "length"],
    ["alllower1!", "upper"],
    ["ALLUPPER1!", "lower"],
    ["NoDigits!!", "number"],
    ["NoSpecial12", "special"],
  ])("flags %s as missing %s", (password, ruleId) => {
    const { results, valid } = checkPassword(password);
    expect(valid).toBe(false);
    expect(results.find((r) => r.id === ruleId).met).toBe(false);
  });

  it("rejects passwords over 72 bytes (bcrypt limit)", () => {
    expect(checkPassword(`Aa1!${"x".repeat(80)}`).tooLong).toBe(true);
    expect(checkPassword(`Aa1!${"x".repeat(80)}`).valid).toBe(false);
  });

  it("does not count whitespace as a special character", () => {
    expect(checkPassword("Passw0rd  ").results.find((r) => r.id === "special").met).toBe(false);
  });

  it("has exactly the five documented rules", () => {
    expect(PASSWORD_RULES.map((r) => r.id)).toEqual(["length", "upper", "lower", "number", "special"]);
  });
});

describe("numeric text fields", () => {
  it("keeps an empty field empty (never 0)", () => {
    expect(sanitizeInteger("")).toBe("");
  });
  it("cleans pasted formats", () => {
    expect(sanitizeInteger("₹ 20,000")).toBe("20000");
    expect(sanitizeInteger("20000.75")).toBe("20000");
    expect(sanitizeInteger("-5")).toBe("5");
    expect(sanitizeInteger("abc")).toBe("");
  });
  it("validates empty, zero, too large and valid values", () => {
    const opts = { label: "your budget", max: 100 };
    expect(parsePositiveInteger("", opts).ok).toBe(false);
    expect(parsePositiveInteger("0", opts).error).toMatch(/at least 1/);
    expect(parsePositiveInteger("101", opts).error).toMatch(/can't be more than 100/);
    expect(parsePositiveInteger("12.5", opts).ok).toBe(false);
    expect(parsePositiveInteger("99", opts)).toEqual({ ok: true, value: 99 });
    expect(parsePositiveInteger("0", { ...opts, min: 0 }).ok).toBe(true);
  });
});

describe("user display helpers never produce 'undefined'", () => {
  it("handles missing values", () => {
    for (const user of [null, undefined, {}, { name: "  " }, { name: undefined, email: undefined }]) {
      expect(getDisplayName(user)).not.toMatch(/undefined|null/);
      expect(getInitials(user)).not.toMatch(/undefined|null/);
    }
    expect(getInitials(null)).toBe("TR");
  });
  it("derives initials and names", () => {
    expect(getInitials({ name: "Asha Rao" })).toBe("AR");
    expect(getInitials({ name: "Madonna" })).toBe("MA");
    expect(getFirstName({ name: "Asha Rao" })).toBe("Asha");
    expect(getDisplayName({ email: "bob@example.com" })).toBe("bob");
  });
});
