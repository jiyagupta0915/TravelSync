from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from bson import ObjectId
from flask import Flask, jsonify, request, session
from dotenv import load_dotenv
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from pymongo.errors import DuplicateKeyError, PyMongoError

from db import database_status, get_db
from recommendation_engine import FEATURES, DF, recommend_destinations, search_start_locations

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
STARTING = pd.read_csv(BASE_DIR / "data" / "starting_locations.csv")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=__import__("os").getenv("FLASK_SECRET_KEY", "change-this-development-secret"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}}, supports_credentials=True)


def serialize_user(user):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
    }


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    try:
        return get_db().users.find_one({"_id": ObjectId(user_id)})
    except (PyMongoError, Exception):
        return None


def require_user():
    user = current_user()
    if user is None:
        return None, (jsonify({"error": "You must be logged in to continue."}), 401)
    return user, None


@app.get("/api/health")
def health():
    db_ok, db_name = database_status()
    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "service": "TravelSync API",
        "destinations": int(len(DF)),
        "model": "Weighted KNN content similarity + constraint ranking",
        "database": {"connected": db_ok, "name": db_name},
    })


@app.post("/api/auth/signup")
def signup():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must contain at least 8 characters."}), 400

    try:
        db = get_db()
        user = {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "created_at": datetime.now(timezone.utc),
        }
        result = db.users.insert_one(user)
        user["_id"] = result.inserted_id
        session.clear()
        session["user_id"] = str(result.inserted_id)
        session.permanent = True
        return jsonify({"user": serialize_user(user)}), 201
    except DuplicateKeyError:
        return jsonify({"error": "An account with this email already exists. Please log in."}), 409
    except PyMongoError as exc:
        return jsonify({"error": f"Could not connect to MongoDB: {exc}"}), 503


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        user = get_db().users.find_one({"email": email})
        if not user or not check_password_hash(user.get("password_hash", ""), password):
            return jsonify({"error": "Invalid email or password."}), 401
        session.clear()
        session["user_id"] = str(user["_id"])
        session.permanent = True
        return jsonify({"user": serialize_user(user)})
    except PyMongoError as exc:
        return jsonify({"error": f"Could not connect to MongoDB: {exc}"}), 503


@app.get("/api/auth/me")
def me():
    user = current_user()
    if not user:
        return jsonify({"user": None}), 200
    return jsonify({"user": serialize_user(user)})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."})


@app.get("/api/features")
def features():
    return jsonify({
        "features": FEATURES,
        "interest_features": [feature for feature in FEATURES if feature not in {"Family", "Couple", "Friends", "Solo"}],
        "traveller_types": ["Family", "Couple", "Friends", "Solo"],
        "importance_levels": {"Must have": 3, "Nice to have": 2, "Optional": 1},
    })


@app.get("/api/start-locations/search")
def start_locations():
    query = request.args.get("q", "")
    try:
        limit = min(max(int(request.args.get("limit", 15)), 1), 15)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    return jsonify({"results": search_start_locations(STARTING, query, limit)})


@app.get("/api/destinations/search")
def destination_search():
    query = request.args.get("q", "").strip().lower()
    limit = min(max(int(request.args.get("limit", 10)), 1), 20)
    if not query:
        rows = DF.head(limit)
    else:
        mask = (
            DF["Destination"].str.lower().str.contains(query, regex=False)
            | DF["State"].str.lower().str.contains(query, regex=False)
        )
        rows = DF[mask].head(limit)
    return jsonify({"results": rows[["Destination", "State", "Region", "Latitude", "Longitude", "Ideal_Days", "Avg_Daily_Budget_INR"]].to_dict("records")})


@app.post("/api/recommend")
def recommend():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON request body is required"}), 400
    try:
        results = recommend_destinations(
            preferences=data["preferences"],
            importance=data["importance"],
            traveller_type=data["traveller_type"],
            duration=data["duration"],
            budget=data["budget"],
            start_lat=data["start_lat"],
            start_lon=data["start_lon"],
            max_distance_km=data["max_distance_km"],
            top_n=min(max(int(data.get("top_n", 6)), 1), 10),
        )
        return jsonify({
            "count": len(results),
            "recommendations": results,
            "rules": {
                "duration": "Destinations within ±1 day receive the strongest duration score",
                "budget": "The entered budget is treated as a target range; nearby costs remain eligible",
                "distance": "Destinations within the selected maximum distance are preferred; a small tolerance is allowed",
            },
        })
    except KeyError as exc:
        return jsonify({"error": f"Missing required field: {exc.args[0]}"}), 400
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Recommendation service error: {exc}"}), 500


@app.get("/api/trips")
def get_trips():
    user, error = require_user()
    if error:
        return error
    try:
        trips = list(get_db().trips.find({"user_id": user["_id"]}).sort("created_at", -1))
        for trip in trips:
            trip["id"] = str(trip.pop("_id"))
            trip["user_id"] = str(trip["user_id"])
            if isinstance(trip.get("created_at"), datetime):
                trip["created_at"] = trip["created_at"].isoformat()
        return jsonify({"trips": trips})
    except PyMongoError as exc:
        return jsonify({"error": f"Could not load trips: {exc}"}), 503


@app.post("/api/trips")
def create_trip():
    user, error = require_user()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    destination = str(data.get("destination", "")).strip()
    if not destination:
        return jsonify({"error": "Destination is required."}), 400

    destination_row = DF[DF["Destination"].str.lower() == destination.lower()].head(1)
    if destination_row.empty:
        return jsonify({"error": "Please choose a destination from the available suggestions."}), 400

    row = destination_row.iloc[0]
    duration_value = int(data["duration"]) if data.get("duration") not in (None, "") else None
    budget_value = float(data["budget"]) if data.get("budget") not in (None, "") else None
    if duration_value is not None and not 1 <= duration_value <= 30:
        return jsonify({"error": "Trip duration must be between 1 and 30 days."}), 400
    if budget_value is not None and budget_value <= 0:
        return jsonify({"error": "Budget must be greater than 0."}), 400

    trip = {
        "user_id": user["_id"],
        "destination": row["Destination"],
        "state": row["State"],
        "region": row["Region"],
        "latitude": float(row["Latitude"]),
        "longitude": float(row["Longitude"]),
        "duration": duration_value,
        "budget": budget_value,
        "traveller_type": data.get("traveller_type"),
        "source": data.get("source", "known-destination"),
        "created_at": datetime.now(timezone.utc),
        "status": "upcoming",
    }
    try:
        result = get_db().trips.insert_one(trip)
        trip["id"] = str(result.inserted_id)
        trip.pop("_id", None)
        trip["user_id"] = str(trip["user_id"])
        trip["created_at"] = trip["created_at"].isoformat()
        return jsonify({"trip": trip}), 201
    except PyMongoError as exc:
        return jsonify({"error": f"Could not save trip: {exc}"}), 503


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
