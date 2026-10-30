# TravelSync Backend (FastAPI)

Async Python FastAPI service for authentication, destination discovery,
recommendation, distance calculation, and saved trips.

## Project layout

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, lifespan, router registration
│   ├── config.py                # Settings loaded from environment variables
│   ├── database.py              # Motor (async MongoDB) connection lifecycle
│   ├── dependencies.py          # get_current_user / require_current_user
│   ├── core/
│   │   ├── security.py          # bcrypt password hashing + JWT tokens
│   │   └── error_handlers.py    # Normalises errors to {"error": "..."}
│   ├── models/
│   │   ├── user.py              # Signup/login request schemas
│   │   ├── trip.py              # Trip request/response schemas
│   │   └── recommend.py         # Recommendation request schema
│   ├── routers/
│   │   ├── auth.py              # /api/auth/*
│   │   ├── trips.py             # /api/trips
│   │   ├── recommend.py         # /api/recommend
│   │   ├── destinations.py      # /api/destinations/search, /api/start-locations/search
│   │   └── meta.py              # /api/health, /api/features
│   ├── services/
│   │   └── recommendation_engine.py   # Weighted-KNN recommendation logic + datasets
│   └── data/
│       ├── ItiNova_India_Destinations_250.csv
│       └── starting_locations.csv
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/Scripts/activate   # Windows (Git Bash)
   # source venv/bin/activate     # macOS / Linux
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create `.env` from `.env.example` and fill in real values (especially
   `JWT_SECRET_KEY` and `MONGODB_URI` if not running MongoDB locally).

4. Make sure MongoDB is running locally, or point `MONGODB_URI` at your
   MongoDB Atlas connection string.

5. Start the API:

   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 5001 --reload
   ```

The API runs on `http://127.0.0.1:5001`. Interactive API docs are
auto-generated at `http://127.0.0.1:5001/docs`.

## Layout additions

```
app/core/        security.py, password_policy.py, csrf.py, rate_limit.py, error_handlers.py
app/models/      user.py, trip.py, recommend.py, packing.py, group.py, booking.py, limits.py
app/routers/     auth, users, trips, trip_manage, packing, stays, travel_health, recommend, destinations,
                 places, groups, bookings, notifications, meta
app/services/    email_service.py, notifications.py (+ existing engines)
tests/           pytest suite (in-memory MongoDB)
```

## Auth model

Authentication uses a JWT stored in an `httpOnly` cookie (`access_token`), set on signup/login and cleared on logout.
Tokens carry `exp`, `sub`, `iat` and a token version; changing or resetting a password bumps the version and signs out
other devices. State-changing requests are checked against `CORS_ORIGINS` (Origin/Referer) in addition to `SameSite=Lax`.
See the repository README for the full security model, environment variables and database index notes.

## Error format

```json
{ "error": "password: Password must contain a number.", "code": "validation_error",
  "details": [{ "field": "password", "message": "Password must contain a number." }] }
```

`error` is always a message safe to show a user. Database problems return 503; unexpected problems return a generic 500.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```
