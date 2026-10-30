import re

import pytest

from app.config import settings
from app.core.password_policy import password_problems
from tests.conftest import GOOD_PASSWORD, ORIGIN, make_client, signup


# ------------------------------------------------------------------ password policy
@pytest.mark.parametrize("pw,missing", [
    ("Sh0rt!a", "at least 8 characters"),
    ("alllower1!", "an uppercase letter"),
    ("ALLUPPER1!", "a lowercase letter"),
    ("NoDigits!!", "a number"),
    ("NoSpecial12", "a special character"),
])
def test_policy_flags_each_missing_requirement(pw, missing):
    assert missing in password_problems(pw)


def test_policy_accepts_good_password_and_rejects_over_72_bytes():
    assert password_problems(GOOD_PASSWORD) == []
    assert "no more than 72 bytes" in password_problems("Aa1!" + "x" * 80)


# ------------------------------------------------------------------ signup
async def test_signup_success_sets_httponly_cookie_and_hides_hash(client):
    r = await client.post("/api/auth/signup", json={"name": "  Asha   Rao ", "email": "  Asha@Example.COM ", "password": GOOD_PASSWORD})
    assert r.status_code == 201
    user = r.json()["user"]
    assert user["email"] == "asha@example.com" and user["name"] == "Asha Rao"
    assert "password_hash" not in r.text and GOOD_PASSWORD not in r.text
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    me = await client.get("/api/auth/me")
    assert me.json()["user"]["email"] == "asha@example.com"


@pytest.mark.parametrize("payload,fragment", [
    ({"name": "A", "email": "a@b.co", "password": GOOD_PASSWORD}, "Name"),
    ({"name": "Alice", "email": "not-an-email", "password": GOOD_PASSWORD}, "valid email"),
    ({"name": "Alice", "email": "a@b.co", "password": "weakpass"}, "Password must contain"),
    ({"name": "Alice", "email": "a@b.co"}, "password"),
    ({"name": "12345", "email": "a@b.co", "password": GOOD_PASSWORD}, "letter"),
])
async def test_signup_validation_errors(client, payload, fragment):
    r = await client.post("/api/auth/signup", json=payload)
    assert r.status_code == 422
    body = r.json()
    assert fragment.lower() in body["error"].lower()
    assert body["code"] == "validation_error" and body["details"]


async def test_signup_malformed_json(client):
    r = await client.post("/api/auth/signup", content=b"{bad json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422 and "json" in r.json()["error"].lower()


async def test_duplicate_signup_conflict_case_insensitive(client, client_b, alice):
    r = await client_b.post("/api/auth/signup", json={"name": "Other", "email": "ALICE@example.com", "password": GOOD_PASSWORD})
    assert r.status_code == 409


async def test_unique_email_index_is_real(fake_db):
    from pymongo.errors import DuplicateKeyError
    await fake_db.users.insert_one({"email": "x@y.co"})
    with pytest.raises(DuplicateKeyError):
        await fake_db.users.insert_one({"email": "x@y.co"})


# ------------------------------------------------------------------ login
async def test_login_does_not_apply_new_password_policy(client, fake_db):
    """An existing user with an old weak password must still be able to log in."""
    from app.core.security import hash_password
    await fake_db.users.insert_one({"name": "Old Timer", "email": "old@example.com", "password_hash": hash_password("weakpass")})
    r = await client.post("/api/auth/login", json={"email": "old@example.com", "password": "weakpass"})
    assert r.status_code == 200 and r.json()["user"]["email"] == "old@example.com"


async def test_login_wrong_password_and_unknown_user_look_identical(client, alice):
    bad = await client.post("/api/auth/login", json={"email": "alice@example.com", "password": "nope"})
    unknown = await client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "nope"})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json()["error"] == unknown.json()["error"]


async def test_login_is_throttled_after_repeated_failures(client, alice):
    for _ in range(settings.login_max_failures):
        assert (await client.post("/api/auth/login", json={"email": "alice@example.com", "password": "bad"})).status_code == 401
    blocked = await client.post("/api/auth/login", json={"email": "alice@example.com", "password": GOOD_PASSWORD})
    assert blocked.status_code == 429


# ------------------------------------------------------------------ session / JWT
async def test_me_without_session_is_null_not_error(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 200 and r.json() == {"user": None}


async def test_logout_clears_session(client, alice):
    assert (await client.post("/api/auth/logout")).status_code == 200
    client.cookies.clear()
    assert (await client.get("/api/trips")).status_code == 401


async def test_tampered_token_is_rejected_and_stale_cookie_cleared(client, alice):
    token = client.cookies.get(settings.cookie_name)
    client.cookies.clear()
    client.cookies.set(settings.cookie_name, token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB"))
    me = await client.get("/api/auth/me")
    assert me.json() == {"user": None}
    assert settings.cookie_name in me.headers.get("set-cookie", "")        # cookie deletion header
    assert (await client.get("/api/trips")).status_code == 401


async def test_expired_token_rejected(client, alice, monkeypatch):
    import jwt
    from datetime import datetime, timedelta, timezone
    expired = jwt.encode({"sub": alice["id"], "tv": 0, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                         settings.jwt_secret_key, algorithm="HS256")
    client.cookies.clear(); client.cookies.set(settings.cookie_name, expired)
    assert (await client.get("/api/trips")).status_code == 401


async def test_token_without_exp_or_with_none_algorithm_rejected(client, alice):
    import jwt
    no_exp = jwt.encode({"sub": alice["id"], "tv": 0}, settings.jwt_secret_key, algorithm="HS256")
    client.cookies.clear(); client.cookies.set(settings.cookie_name, no_exp)
    assert (await client.get("/api/trips")).status_code == 401
    unsigned = jwt.encode({"sub": alice["id"], "tv": 0, "exp": 9999999999}, key=None, algorithm="none")
    client.cookies.clear(); client.cookies.set(settings.cookie_name, unsigned)
    assert (await client.get("/api/trips")).status_code == 401


async def test_database_failure_on_me_is_503_not_logged_out(client, alice, monkeypatch):
    from pymongo.errors import ServerSelectionTimeoutError
    from app import dependencies

    class Boom:
        async def find_one(self, *a, **k):
            raise ServerSelectionTimeoutError("mongodb://user:secret@host timed out")

    class FakeDb:
        users = Boom()

    monkeypatch.setattr(dependencies, "get_db", lambda: FakeDb())
    r = await client.get("/api/auth/me")
    assert r.status_code == 503
    assert "secret" not in r.text and "mongodb://" not in r.text


async def test_database_error_never_leaks_details(client, alice, monkeypatch):
    from pymongo.errors import AutoReconnect
    from app.routers import trips as trips_router

    class Cursor:
        def sort(self, *a, **k): return self
        def __aiter__(self): return self
        async def __anext__(self): raise AutoReconnect("host=10.0.0.5:27017 password=hunter2")

    class Coll:
        def find(self, *a, **k): return Cursor()

    class FakeDb:
        trips = Coll()

    monkeypatch.setattr(trips_router, "get_db", lambda: FakeDb())
    r = await client.get("/api/trips")
    assert r.status_code == 503 and r.json()["code"] == "service_unavailable"
    assert "hunter2" not in r.text and "10.0.0.5" not in r.text


async def test_unhandled_exception_returns_generic_500(client, alice, monkeypatch):
    from app.routers import trips as trips_router

    def explode():
        raise ValueError("internal secret detail /etc/passwd")

    monkeypatch.setattr(trips_router, "get_db", explode)
    r = await client.get("/api/trips")
    assert r.status_code == 500 and "passwd" not in r.text and r.json()["code"] == "server_error"


# ------------------------------------------------------------------ password change
async def test_change_password_revokes_other_sessions(client, client_b, alice):
    await client_b.post("/api/auth/login", json={"email": "alice@example.com", "password": GOOD_PASSWORD})
    assert (await client_b.get("/api/trips")).status_code == 200

    r = await client.post("/api/auth/change-password", json={"current_password": GOOD_PASSWORD, "new_password": "N3w!Passw0rd#"})
    assert r.status_code == 200
    assert (await client.get("/api/trips")).status_code == 200            # this session was re-issued
    assert (await client_b.get("/api/trips")).status_code == 401          # the other device is signed out
    ok = await client_b.post("/api/auth/login", json={"email": "alice@example.com", "password": "N3w!Passw0rd#"})
    assert ok.status_code == 200


async def test_change_password_rules(client, alice):
    wrong = await client.post("/api/auth/change-password", json={"current_password": "wrong", "new_password": "N3w!Passw0rd#"})
    assert wrong.status_code == 403
    weak = await client.post("/api/auth/change-password", json={"current_password": GOOD_PASSWORD, "new_password": "weak"})
    assert weak.status_code == 422
    same = await client.post("/api/auth/change-password", json={"current_password": GOOD_PASSWORD, "new_password": GOOD_PASSWORD})
    assert same.status_code == 422


async def test_change_password_requires_login(client):
    r = await client.post("/api/auth/change-password", json={"current_password": "x", "new_password": GOOD_PASSWORD})
    assert r.status_code == 401


# ------------------------------------------------------------------ password recovery (provider gated)
async def test_recovery_reports_unavailable_without_email_provider(client, alice):
    assert (await client.get("/api/auth/recovery-status")).json() == {"available": False}
    r = await client.post("/api/auth/forgot-password", json={"email": "alice@example.com"})
    assert r.status_code == 503 and "not configured" in r.json()["error"]


async def test_recovery_flow_with_provider(client, client_b, alice, smtp_configured):
    r = await client.post("/api/auth/forgot-password", json={"email": "alice@example.com"})
    assert r.status_code == 200 and len(smtp_configured) == 1
    token = re.search(r"token=([\w-]+)", smtp_configured[0]["body"]).group(1)

    # unknown account: same response, no email
    r2 = await client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r2.status_code == 200 and r2.json() == r.json() and len(smtp_configured) == 1

    weak = await client.post("/api/auth/reset-password", json={"token": token, "new_password": "weak"})
    assert weak.status_code == 422
    ok = await client.post("/api/auth/reset-password", json={"token": token, "new_password": "R3set!Passw0rd"})
    assert ok.status_code == 200
    reuse = await client.post("/api/auth/reset-password", json={"token": token, "new_password": "An0ther!Passw0rd"})
    assert reuse.status_code == 400                                              # single use
    assert (await client_b.post("/api/auth/login", json={"email": "alice@example.com", "password": "R3set!Passw0rd"})).status_code == 200
    assert (await client_b.post("/api/auth/login", json={"email": "alice@example.com", "password": GOOD_PASSWORD})).status_code == 401


async def test_reset_with_bogus_or_expired_token(client, alice, smtp_configured, fake_db):
    assert (await client.post("/api/auth/reset-password", json={"token": "x" * 40, "new_password": GOOD_PASSWORD})).status_code == 400
    await client.post("/api/auth/forgot-password", json={"email": "alice@example.com"})
    token = re.search(r"token=([\w-]+)", smtp_configured[0]["body"]).group(1)
    from datetime import datetime, timedelta
    await fake_db.password_resets.update_many({}, {"$set": {"expires_at": datetime.utcnow() - timedelta(minutes=1)}})
    assert (await client.post("/api/auth/reset-password", json={"token": token, "new_password": GOOD_PASSWORD})).status_code == 400


# ------------------------------------------------------------------ CSRF / CORS
async def test_cross_site_origin_blocked_on_state_changing_request(alice, client):
    async with make_client() as evil:
        evil.cookies.set(settings.cookie_name, client.cookies.get(settings.cookie_name))
        r = await evil.post("/api/trips", json={"destination": "Goa"}, headers={"Origin": "https://evil.example"})
        assert r.status_code == 403 and r.json()["code"] == "forbidden"


async def test_missing_origin_with_cookie_blocked_but_allowed_without_cookie(client, alice):
    no_origin = {"Origin": ""}
    async with make_client() as c:
        c.headers.pop("Origin")
        c.cookies.set(settings.cookie_name, client.cookies.get(settings.cookie_name))
        assert (await c.post("/api/trips", json={"destination": "Goa"})).status_code == 403
    async with make_client() as anon:
        anon.headers.pop("Origin")
        assert (await anon.post("/api/auth/logout")).status_code == 200      # no ambient credential, nothing to forge


async def test_cors_allows_only_configured_origin(client):
    ok = await client.options("/api/trips", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == ORIGIN
    assert ok.headers.get("access-control-allow-credentials") == "true"
    bad = await client.options("/api/trips", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers


# ------------------------------------------------------------------ production config guard
def test_production_refuses_weak_configuration():
    from app.config import Settings, validate_settings
    prod = Settings()
    prod.environment = "production"
    prod.jwt_secret_key = "change-this-development-secret"
    prod.cookie_secure = False
    prod.cors_origins = ["*"]
    with pytest.raises(RuntimeError) as exc:
        validate_settings(prod)
    message = str(exc.value)
    assert "JWT_SECRET_KEY" in message and "COOKIE_SECURE" in message and "CORS_ORIGINS" in message
    prod.jwt_secret_key = "x" * 40; prod.cookie_secure = True; prod.cors_origins = ["https://app.example.com"]
    validate_settings(prod)
