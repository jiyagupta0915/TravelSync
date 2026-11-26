# TravelSync evaluation scripts

These scripts produce the evaluation figures in Chapter 3 of the end-semester
report. Run them from the `backend` folder with the project's virtual
environment active (`pip install -r requirements-dev.txt`).

| Script | Report tables | Needs a running server? |
|---|---|---|
| `recommendation_eval.py` | Table 3.9: Precision@5, top-result relevance, random baseline, distance/budget checks, engine time | No |
| `api_benchmark.py` | Table 3.7 (response times) and Table 3.8 (throughput) | Yes |
| `run_server_inmemory.py` | Starts the backend on port 5001 with an in-memory database | – |

## 1. Recommendation accuracy and constraint checks

    python evaluation/recommendation_eval.py

- **Precision@5:** 48 requests (12 interests x 4 traveller types), each asking
  for one interest at the highest importance. A result is relevant if the
  destination's dataset score for that interest is at least 0.5 (also
  reported for 0.7). The random baseline is the share of all
  destination/interest pairs that meet the same threshold.
- **Constraint checks:** 300 random requests from Ludhiana (random seed 42),
  counting results inside the maximum distance, inside the 10% tolerance,
  and above 125% of the budget, and timing the engine.

These numbers come from the bundled dataset and a fixed random seed, so they
are the same on every computer; only the engine time depends on the machine.
Results are saved to `recommendation_results.json`.

## 2. Response time and throughput

Terminal 1 (in-memory database, nothing to install):

    python evaluation/run_server_inmemory.py

Terminal 2:

    python evaluation/api_benchmark.py

The benchmark creates four demo accounts, a trip, a group with messages,
suggestions and votes, and three bookings, then:

- calls each endpoint 10 times to warm up and 200 times measured (login 20
  times), reporting the median and 95th percentile;
- runs 16 concurrent clients against each endpoint for 10 seconds and
  reports requests per second and errors.

Results are saved to `api_results.json`, including the machine details.
These numbers depend on the computer, so they will differ slightly between
runs and machines. Run them against a development database only.
