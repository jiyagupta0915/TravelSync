"""
API response time (Table 3.7) and throughput (Table 3.8) for TravelSync.

1. Start the backend in another terminal, either normally
       uvicorn app.main:app --port 5001
   or with a throw-away in-memory database (no MongoDB needed):
       python evaluation/run_server_inmemory.py
2. From the backend folder run:
       python evaluation/api_benchmark.py
   Options: --base-url http://127.0.0.1:5001  --origin http://localhost:5173

The script first creates four demo accounts, a trip, a group with chat
messages, suggestions and votes, and three bookings (it logs in instead if
the accounts already exist). Only use it against a development database.
"""

import argparse
import asyncio
import json
import os
import platform
import statistics
import time
from pathlib import Path

import httpx

PASSWORD = "Travel@2026"
USERS = [("Shreya", "shreya@travelsync.demo"), ("Jiya Gupta", "jiya@travelsync.demo"),
         ("Himani Nayyar", "himani@travelsync.demo"), ("Molika Goela", "molika@travelsync.demo")]
FEATURES = ["Mountain", "Beach", "Nature", "Adventure", "Culture", "Relaxation",
            "Nightlife", "Spiritual", "Trekking", "Photography", "Food", "Heritage"]


def recommend_body():
    prefs = {f: 0.0 for f in FEATURES}
    prefs.update(Mountain=1, Nature=1, Trekking=0.8, Photography=0.7)
    imp = {f: 0.0 for f in FEATURES}
    imp.update(Mountain=3, Nature=2, Trekking=2, Photography=1)
    return {"preferences": prefs, "importance": imp, "traveller_type": "Friends",
            "duration": 5, "budget": 25000, "start_lat": 30.90, "start_lon": 75.85,
            "max_distance_km": 600, "top_n": 6}


def login_or_signup(client, name, email):
    r = client.post("/api/auth/signup", json={"name": name, "email": email, "password": PASSWORD})
    if r.status_code != 201:
        r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    r.raise_for_status()


def seed(base_url, origin):
    clients = []
    for name, email in USERS:
        c = httpx.Client(base_url=base_url, headers={"Origin": origin}, timeout=30)
        login_or_signup(c, name, email)
        clients.append(c)
    owner = clients[0]
    trip = owner.post("/api/trips", json={"destination": "Manali", "duration": 5, "budget": 25000,
                                          "traveller_type": "Friends", "source": "recommendation"}).json()
    trip_id = trip.get("trip", trip)["id"]
    owner.patch(f"/api/trips/{trip_id}", json={"start_date": "2026-12-18", "end_date": "2026-12-22"})
    owner.post(f"/api/trips/{trip_id}/packing-list", json={})
    group = owner.post("/api/groups", json={"name": "Winter Himachal Trip",
                                            "description": "Planning our December break"}).json()
    group = group.get("group", group)
    for c in clients[1:]:
        c.post("/api/groups/join", json={"invite_code": group["invite_code"]})
    for c, text in zip(clients, ["Hi everyone!", "Somewhere with snow please.",
                                 "Budget around 25k each.", "Manali looks good."]):
        c.post(f"/api/groups/{group['id']}/messages", json={"text": text})
    s = owner.post(f"/api/groups/{group['id']}/suggestions",
                   json={"destination": "Manali", "note": "Snow and treks", "budget": 25000, "duration": 5}).json()
    s = s.get("suggestion", s)
    for c in clients:
        c.put(f"/api/groups/{group['id']}/suggestions/{s['id']}/vote")
    for b in [dict(kind="bus", title="Volvo Chandigarh to Manali", provider="HRTC", reference="HR1",
                   start_date="2026-12-18", amount_inr=1450, trip_id=trip_id),
              dict(kind="hotel", title="Riverside cottage", provider="Direct", reference="OM1",
                   start_date="2026-12-18", end_date="2026-12-22", amount_inr=9600, trip_id=trip_id),
              dict(kind="activity", title="Paragliding", provider="Local", reference="SV1",
                   start_date="2026-12-20", amount_inr=3000, trip_id=trip_id)]:
        owner.post("/api/bookings", json=b)
    for c in clients:
        c.close()
    return trip_id, group["id"]


def endpoints(trip_id, group_id):
    body = recommend_body()
    return [
        ("GET /api/health", "GET", "/api/health", None),
        ("GET /api/trips", "GET", "/api/trips", None),
        ("GET /api/trips/{id}/packing-list", "GET", f"/api/trips/{trip_id}/packing-list", None),
        ("GET /api/bookings", "GET", "/api/bookings", None),
        ("GET /api/groups/{id}/messages", "GET", f"/api/groups/{group_id}/messages", None),
        ("GET /api/places/{destination}", "GET", "/api/places/Manali", None),
        ("GET /api/destinations/search", "GET", "/api/destinations/search?q=man", None),
        ("POST /api/chat", "POST", "/api/chat", {"message": "Top places in Manali"}),
        ("POST /api/recommend", "POST", "/api/recommend", body),
        ("GET /api/travel-health/{destination}", "GET", "/api/travel-health/Manali", None),
    ]


def response_times(base_url, origin, eps, warmup=10, runs=200):
    out = {}
    with httpx.Client(base_url=base_url, headers={"Origin": origin}, timeout=30) as c:
        c.post("/api/auth/login", json={"email": USERS[0][1], "password": PASSWORD}).raise_for_status()
        for name, method, path, body in eps:
            def call():
                r = c.request(method, path, json=body)
                r.raise_for_status()
            for _ in range(warmup):
                call()
            t = []
            for _ in range(runs):
                start = time.perf_counter(); call(); t.append((time.perf_counter() - start) * 1000)
            t.sort()
            out[name] = {"median_ms": statistics.median(t), "p95_ms": t[int(0.95 * runs) - 1]}
        t = []
        for _ in range(20):  # login is slow on purpose (bcrypt), so fewer runs
            start = time.perf_counter()
            c.post("/api/auth/login", json={"email": USERS[0][1], "password": PASSWORD}).raise_for_status()
            t.append((time.perf_counter() - start) * 1000)
        t.sort()
        out["POST /api/auth/login"] = {"median_ms": statistics.median(t), "p95_ms": t[18]}
    return out


async def throughput(base_url, origin, eps, clients=16, seconds=10):
    wanted = {"GET /api/trips", "GET /api/groups/{id}/messages", "GET /api/places/{destination}",
              "POST /api/chat", "POST /api/recommend", "GET /api/travel-health/{destination}"}
    out = {}
    async with httpx.AsyncClient(base_url=base_url, headers={"Origin": origin}, timeout=30,
                                 limits=httpx.Limits(max_connections=clients * 2)) as c:
        (await c.post("/api/auth/login", json={"email": USERS[0][1], "password": PASSWORD})).raise_for_status()
        for name, method, path, body in eps:
            if name not in wanted:
                continue
            ok = errors = 0
            stop = time.perf_counter() + seconds

            async def worker():
                nonlocal ok, errors
                while time.perf_counter() < stop:
                    r = await c.request(method, path, json=body)
                    if r.status_code < 400:
                        ok += 1
                    else:
                        errors += 1
            start = time.perf_counter()
            await asyncio.gather(*[worker() for _ in range(clients)])
            out[name] = {"requests_per_second": ok / (time.perf_counter() - start), "errors": errors}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:5001")
    ap.add_argument("--origin", default="http://localhost:5173")
    a = ap.parse_args()
    machine = {"python": platform.python_version(), "os": platform.platform(),
               "processor": platform.processor() or platform.machine(), "cpu_count": os.cpu_count()}
    print("Machine:", machine)
    print("Seeding demo data ...")
    trip_id, group_id = seed(a.base_url, a.origin)
    eps = endpoints(trip_id, group_id)
    print("\nResponse times (200 calls each after 10 warm-up calls):")
    rt = response_times(a.base_url, a.origin, eps)
    for name, v in sorted(rt.items(), key=lambda kv: kv[1]["median_ms"]):
        print(f"  {name:<42} median {v['median_ms']:7.1f} ms   p95 {v['p95_ms']:7.1f} ms")
    print("\nThroughput (16 concurrent clients, 10 s per endpoint):")
    tp = asyncio.run(throughput(a.base_url, a.origin, eps))
    for name, v in sorted(tp.items(), key=lambda kv: -kv[1]["requests_per_second"]):
        print(f"  {name:<42} {v['requests_per_second']:7.1f} req/s   errors {v['errors']}")
    out = Path(__file__).with_name("api_results.json")
    out.write_text(json.dumps({"machine": machine, "response_times": rt, "throughput": tp}, indent=2))
    print("\nSaved", out)


if __name__ == "__main__":
    main()
