# TravelSync Backend

Python Flask API for authentication, destination discovery, recommendation, distance calculation, and saved trips.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` from `.env.example`.
4. Make sure MongoDB is running locally or replace `MONGODB_URI` with your MongoDB Atlas connection string.
5. Start the API:

```bash
python app.py
```

The API runs on `http://127.0.0.1:5001`.
