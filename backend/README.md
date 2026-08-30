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

## Auth model

Authentication uses a JWT stored in an `httpOnly` cookie (`access_token`),
set on signup/login and cleared on logout. This is the stateless
equivalent of the previous Flask session cookie - no server-side session
store is needed, and the frontend's `credentials: "include"` fetch calls
work unchanged.
