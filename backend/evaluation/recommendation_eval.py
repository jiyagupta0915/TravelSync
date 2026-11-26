"""
Recommendation accuracy, constraint adherence and engine speed for TravelSync.

Reproduces the figures in Table 3.9 of the end-semester report.

Run from the backend folder:
    python evaluation/recommendation_eval.py

No server or database is needed: the script calls the recommendation engine
directly on the bundled destination dataset.
"""

import json
import os
import platform
import random
import statistics
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services import recommendation_engine as R  # noqa: E402

FEATURES = R.INTEREST_FEATURES          # the 12 interests
TYPES = R.TRAVELLER_TYPES               # Family, Couple, Friends, Solo
DF = R.DF                               # the 250-destination dataset


def interest_score(destination: str, interest: str) -> float:
    return float(DF.loc[DF.Destination == destination, interest].iloc[0])


def precision_at_5(threshold: float):
    """For every interest x traveller type, ask for that one interest at the
    highest importance (no budget/distance limits, 4-day trip) and count how
    many of the top 5 results score >= threshold on that interest."""
    relevant = total = top1_hits = queries = 0
    misses = []
    for interest in FEATURES:
        for ttype in TYPES:
            prefs = {f: 0.0 for f in FEATURES}
            prefs[interest] = 1.0
            importance = {f: 0.0 for f in FEATURES}
            importance[interest] = 3.0
            results = R.recommend_destinations(prefs, importance, ttype, 4,
                                               None, None, None, None, 5)
            scores = [interest_score(r["Destination"], interest) for r in results]
            relevant += sum(s >= threshold for s in scores)
            total += len(scores)
            queries += 1
            top1_hits += bool(scores) and scores[0] >= threshold
            for r, s in zip(results, scores):
                if s < threshold:
                    misses.append({
                        "interest": interest, "traveller_type": ttype,
                        "destination": r["Destination"], "interest_score": s,
                        "traveller_type_score": float(DF.loc[DF.Destination == r["Destination"], ttype].iloc[0]),
                    })
    baseline = float((DF[FEATURES] >= threshold).values.mean())
    return {
        "threshold": threshold,
        "relevant": relevant, "total": total,
        "precision_at_5": relevant / total,
        "top1_relevant": top1_hits, "queries": queries,
        "random_baseline": baseline,
        "non_relevant_results": misses,
    }


def constraint_check(n_requests: int = 300, seed: int = 42):
    """Random requests from Ludhiana; checks distance and budget limits and
    times the engine."""
    random.seed(seed)
    within_max = within_tol = over_budget = results_total = 0
    times_ms = []
    for _ in range(n_requests):
        prefs = {f: round(random.random(), 2) for f in FEATURES}
        importance = {f: random.choice([0, 1, 2, 3]) for f in FEATURES}
        importance[random.choice(FEATURES)] = 3
        duration = random.randint(2, 10)
        max_km = random.choice([300, 600, 1000, 2000])
        budget = random.choice([10000, 20000, 40000, 80000])
        ttype = random.choice(TYPES)
        start = time.perf_counter()
        results = R.recommend_destinations(prefs, importance, ttype, duration,
                                           budget, 30.90, 75.85, max_km, 6)
        times_ms.append((time.perf_counter() - start) * 1000)
        for r in results:
            results_total += 1
            within_max += r["distance_km"] <= max_km
            within_tol += r["distance_km"] <= 1.10 * max_km
            over_budget += r["estimated_trip_budget_inr"] > 1.25 * budget
    times_ms.sort()
    return {
        "requests": n_requests, "results": results_total,
        "within_max_distance": within_max,
        "within_10pct_tolerance": within_tol,
        "over_125pct_budget": over_budget,
        "engine_ms_median": statistics.median(times_ms),
        "engine_ms_p95": times_ms[int(0.95 * len(times_ms)) - 1],
    }


def machine_info():
    info = {"python": platform.python_version(), "os": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "cpu_count": os.cpu_count()}
    try:  # optional, only if psutil is installed
        import psutil
        info["ram_gb"] = round(psutil.virtual_memory().total / 2**30, 1)
    except ImportError:
        pass
    return info


def main():
    report = {
        "machine": machine_info(),
        "precision_0_5": precision_at_5(0.5),
        "precision_0_7": precision_at_5(0.7),
        "constraints": constraint_check(),
    }
    p5, p7, c = report["precision_0_5"], report["precision_0_7"], report["constraints"]
    print("Machine:", report["machine"])
    print(f"Precision@5 (>=0.5): {p5['precision_at_5']:.2%} ({p5['relevant']} of {p5['total']})")
    print(f"Precision@5 (>=0.7): {p7['precision_at_5']:.2%} ({p7['relevant']} of {p7['total']})")
    print(f"Top result relevant (>=0.5): {p5['top1_relevant']} of {p5['queries']}")
    print(f"Random baseline (>=0.5): {p5['random_baseline']:.1%}")
    print(f"Within max distance: {c['within_max_distance']} of {c['results']} "
          f"({c['within_max_distance'] / c['results']:.1%})")
    print(f"Within 10% tolerance: {c['within_10pct_tolerance']} of {c['results']}")
    print(f"Over 125% of budget: {c['over_125pct_budget']}")
    print(f"Engine time: median {c['engine_ms_median']:.1f} ms, p95 {c['engine_ms_p95']:.1f} ms")
    print("Non-relevant results (>=0.5):")
    for m in p5["non_relevant_results"]:
        print(f"  {m['interest']:<11} {m['traveller_type']:<8} {m['destination']:<14} "
              f"interest={m['interest_score']:.2f} traveller_type={m['traveller_type_score']:.2f}")
    out = Path(__file__).with_name("recommendation_results.json")
    out.write_text(json.dumps(report, indent=2))
    print("Saved", out)


if __name__ == "__main__":
    main()
