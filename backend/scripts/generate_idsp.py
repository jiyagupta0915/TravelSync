"""
Synthetic IDSP-style outbreak data generator for TravelSync (Health & Safety module).

!! THIS DATA IS SYNTHETIC. It is NOT real surveillance data. !!
Every row carries source="synthetic". Do not present it to users as real outbreak history.

Schema mirrors the Dataful/IDSP weekly outbreak dataset (minus LGD codes and
district_as_per_source), so real data can be swapped in later without code changes:

    year, week, outbreak_starting_date, reporting_date, state,
    district_as_per_lgd, disease_illness_name, status, cases, deaths, units, source

Everything is rule-based using broad, textbook-level assumptions (e.g. dengue peaks
in the monsoon/post-monsoon, chickenpox and measles in late winter/spring). Those
assumptions are MINE, not measured from real data - they only make the pipeline
behave plausibly while you build it.

A few "planted" anomalies are written to a separate ground-truth file so you can check
that your Isolation Forest code runs and finds them. That validates the CODE, not the
epidemiology.

Usage:
    python generate_synthetic_idsp.py                       # defaults
    python generate_synthetic_idsp.py --seed 7 --rows-per-year 2000 --out backend/app/data
"""

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Geography: the 35 states/UTs that appear in the TravelSync destinations CSV.
# (district names are real district names; the outbreaks attached to them are fake)
# ----------------------------------------------------------------------------
STATE_DISTRICTS = {
    "Andhra Pradesh": ["Chittoor", "Visakhapatnam", "Guntur", "Krishna", "Kurnool"],
    "Arunachal Pradesh": ["Tawang", "West Kameng", "Papum Pare", "Lohit"],
    "Assam": ["Kamrup Metropolitan", "Jorhat", "Dibrugarh", "Cachar", "Tinsukia"],
    "Bihar": ["Patna", "Gaya", "Muzaffarpur", "Darbhanga"],
    "Chandigarh": ["Chandigarh"],
    "Chhattisgarh": ["Raipur", "Bilaspur", "Durg", "Janjgir-Champa"],
    "Daman and Diu": ["Daman", "Diu"],
    "Delhi": ["New Delhi", "South Delhi", "North Delhi"],
    "Goa": ["North Goa", "South Goa"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Kachchh"],
    "Himachal Pradesh": ["Kullu", "Shimla", "Kangra", "Mandi", "Solan"],
    "Jammu and Kashmir": ["Srinagar", "Jammu", "Anantnag", "Baramulla"],
    "Jharkhand": ["Ranchi", "Dhanbad", "East Singhbhum", "Hazaribagh"],
    "Karnataka": ["Bengaluru Urban", "Bengaluru Rural", "Mysuru", "Udupi", "Belagavi", "Kodagu"],
    "Kerala": ["Thiruvananthapuram", "Ernakulam", "Kozhikode", "Thrissur", "Kasaragod", "Idukki"],
    "Ladakh": ["Leh", "Kargil"],
    "Lakshadweep": ["Lakshadweep"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain"],
    "Maharashtra": ["Pune", "Thane", "Nashik", "Nagpur", "Amravati", "Gondia", "Kolhapur"],
    "Manipur": ["Imphal West", "Imphal East", "Churachandpur"],
    "Meghalaya": ["East Khasi Hills", "West Garo Hills", "Ri Bhoi"],
    "Mizoram": ["Aizawl", "Lunglei"],
    "Nagaland": ["Kohima", "Dimapur"],
    "Odisha": ["Khordha", "Puri", "Cuttack", "Ganjam", "Koraput"],
    "Puducherry": ["Puducherry"],
    "Punjab": ["Amritsar", "Ludhiana", "Jalandhar", "Patiala"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Bikaner", "Ajmer"],
    "Sikkim": ["East Sikkim", "West Sikkim", "North Sikkim"],
    "Tamil Nadu": ["Chennai", "Madurai", "Perambalur", "Dharmapuri", "Coimbatore", "Nilgiris"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad"],
    "Tripura": ["West Tripura", "North Tripura"],
    "Uttar Pradesh": ["Lucknow", "Varanasi", "Agra", "Gorakhpur", "Prayagraj"],
    "Uttarakhand": ["Dehradun", "Nainital", "Haridwar", "Chamoli", "Pauri Garhwal"],
    "West Bengal": ["Kolkata", "Darjeeling", "Howrah", "Jalpaiguri", "Murshidabad"],
}

# Relative chance that a state files an outbreak report (big states report more).
STATE_REPORTING_WEIGHT = {
    "Maharashtra": 3.0, "Karnataka": 3.0, "Tamil Nadu": 3.0, "Kerala": 3.0,
    "Gujarat": 2.5, "Uttar Pradesh": 2.0, "Madhya Pradesh": 2.5, "West Bengal": 2.5,
    "Odisha": 2.5, "Andhra Pradesh": 2.5, "Telangana": 2.0, "Assam": 2.5,
    "Rajasthan": 1.8, "Chhattisgarh": 2.0, "Bihar": 1.2, "Jharkhand": 1.2,
    "Punjab": 1.2, "Himachal Pradesh": 1.2, "Uttarakhand": 1.2, "Delhi": 0.8,
    "Goa": 0.7, "Jammu and Kashmir": 0.8, "Meghalaya": 0.9, "Tripura": 0.8,
    "Arunachal Pradesh": 0.7, "Mizoram": 0.7, "Manipur": 0.6, "Nagaland": 0.6,
    "Sikkim": 0.5, "Ladakh": 0.2, "Puducherry": 0.5, "Chandigarh": 0.3,
    "Daman and Diu": 0.15, "Lakshadweep": 0.1,
}

HILL_STATES = {"Himachal Pradesh", "Uttarakhand", "Jammu and Kashmir", "Ladakh", "Sikkim", "Arunachal Pradesh"}
SOUTH_COASTAL = {"Kerala", "Tamil Nadu", "Karnataka", "Goa", "Andhra Pradesh", "Odisha", "Maharashtra", "Puducherry"}
JE_STATES = {"Assam", "Uttar Pradesh", "Bihar", "West Bengal", "Odisha", "Manipur", "Meghalaya", "Tripura", "Jharkhand"}

# ----------------------------------------------------------------------------
# Diseases: weight (how often reported), typical cases, death behaviour, seasonality
# season = 12 relative weights Jan..Dec
# ----------------------------------------------------------------------------
def _s(*w):
    a = np.array(w, dtype=float)
    return a / a.sum()

DISEASES = {
    # name: (group, weight, median_cases, sigma, p_death, max_cfr, season)
    "Acute Diarrheal Disease": ("gi", 20, 22, 0.8, 0.02, 0.02, _s(2, 2, 3, 5, 7, 9, 10, 10, 8, 5, 3, 2)),
    "Acute Gastroenteritis": ("gi", 10, 24, 0.8, 0.02, 0.02, _s(2, 2, 3, 5, 7, 9, 10, 10, 8, 5, 3, 2)),
    "Suspected Food Poisoning": ("gi", 8, 28, 0.9, 0.01, 0.02, _s(3, 3, 5, 8, 9, 7, 7, 7, 6, 5, 4, 4)),
    "Food Poisoning": ("gi", 6, 26, 0.9, 0.01, 0.02, _s(3, 3, 5, 8, 9, 7, 7, 7, 6, 5, 4, 4)),
    "Dysentery": ("gi", 4, 16, 0.7, 0.01, 0.02, _s(2, 2, 3, 5, 7, 8, 9, 9, 7, 5, 3, 2)),
    "Cholera": ("gi", 3, 15, 0.8, 0.05, 0.04, _s(1, 1, 2, 3, 5, 9, 12, 12, 9, 5, 2, 1)),
    "Viral Hepatitis": ("gi", 4, 14, 0.7, 0.03, 0.03, _s(2, 2, 3, 4, 5, 8, 11, 11, 9, 6, 3, 2)),
    "Enteric Fever": ("gi", 3, 12, 0.7, 0.01, 0.02, _s(2, 2, 3, 5, 7, 8, 9, 9, 7, 5, 3, 2)),
    "Dengue": ("vector", 9, 14, 0.9, 0.03, 0.03, _s(1, 1, 1, 1, 2, 4, 9, 13, 16, 15, 9, 3)),
    "Chikungunya": ("vector", 3, 18, 0.9, 0.00, 0.00, _s(1, 1, 1, 1, 2, 4, 8, 12, 14, 14, 9, 3)),
    "Malaria": ("vector", 5, 10, 0.8, 0.03, 0.05, _s(1, 1, 2, 3, 5, 9, 13, 14, 12, 8, 3, 1)),
    "Leptospirosis": ("zoonotic", 2, 12, 0.8, 0.08, 0.08, _s(1, 1, 1, 2, 3, 8, 13, 14, 13, 9, 4, 1)),
    "Japanese Encephalitis": ("vector", 1.5, 6, 0.7, 0.35, 0.25, _s(1, 1, 1, 2, 4, 9, 14, 14, 12, 8, 3, 1)),
    "Chickenpox": ("vpd", 8, 12, 0.8, 0.0, 0.0, _s(11, 13, 14, 12, 8, 4, 2, 2, 2, 3, 6, 9)),
    "Measles": ("vpd", 5, 15, 0.8, 0.01, 0.02, _s(11, 13, 14, 12, 8, 4, 2, 2, 2, 3, 5, 9)),
    "Mumps": ("vpd", 2, 10, 0.7, 0.0, 0.0, _s(10, 12, 13, 11, 8, 5, 3, 3, 3, 4, 6, 9)),
    "Rubella": ("vpd", 1.5, 9, 0.7, 0.0, 0.0, _s(10, 12, 13, 11, 8, 5, 3, 3, 3, 4, 6, 9)),
    "Diphtheria": ("vpd", 1, 4, 0.7, 0.2, 0.3, _s(5, 5, 5, 5, 5, 6, 7, 8, 9, 10, 9, 7)),
    "Fever with Rash": ("vpd", 3, 14, 0.8, 0.0, 0.0, _s(9, 11, 12, 11, 8, 5, 4, 4, 4, 5, 7, 8)),
    "Influenza": ("resp", 3, 24, 0.8, 0.03, 0.03, _s(10, 9, 7, 4, 3, 4, 10, 12, 10, 6, 5, 9)),
    "Viral Fever": ("resp", 4, 26, 0.8, 0.01, 0.02, _s(5, 4, 4, 4, 5, 7, 11, 13, 12, 9, 6, 5)),
    "Rabies": ("zoonotic", 1.5, 1, 0.2, 0.95, 1.0, _s(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)),
    "Crimean-Congo Haemorrhagic Fever (CCHF)": ("zoonotic", 0.25, 1, 0.1, 0.45, 1.0, _s(1, 1, 2, 5, 8, 10, 10, 9, 5, 2, 1, 1)),
}

STATUS_RECENT = (["Under Surveillance", "Under Control"], [0.92, 0.08])
STATUS_OLDER = (["Under Surveillance", "Under Control", "Closed"], [0.35, 0.40, 0.25])


def state_disease_multiplier(state, disease, group):
    m = 1.0
    if state in HILL_STATES and group == "vector":
        m *= 0.3
    if state in SOUTH_COASTAL and disease in ("Leptospirosis", "Dengue", "Chikungunya"):
        m *= 1.8
    if disease == "Japanese Encephalitis":
        m *= 2.5 if state in JE_STATES else 0.05
    if disease == "Crimean-Congo Haemorrhagic Fever (CCHF)":
        m *= 12 if state in ("Gujarat", "Rajasthan") else 0.1
    if disease == "Cholera" and state in ("Odisha", "West Bengal", "Maharashtra", "Gujarat"):
        m *= 1.6
    if state in ("Rajasthan", "Ladakh") and group == "vector":
        m *= 0.6
    return m


def draw_cases_deaths(rng, disease, scale=1.0):
    _, _, med, sigma, p_death, max_cfr, _ = DISEASES[disease]
    cases = max(1, int(round(rng.lognormal(np.log(med * scale), sigma))))
    deaths = 0
    if disease == "Rabies":
        cases = 1
        deaths = 1 if rng.random() < 0.95 else 0
    elif disease.startswith("Crimean"):
        cases = int(rng.choice([1, 1, 1, 2]))
        deaths = int(rng.random() < p_death) * 1
    elif rng.random() < p_death and max_cfr > 0:
        deaths = int(min(cases, max(1, round(cases * rng.uniform(0.02, max_cfr) + rng.integers(0, 2)))))
    return cases, deaths


def build_rows(rng, start_year, end_year, rows_per_year, last_date):
    states = list(STATE_DISTRICTS)
    state_w = np.array([STATE_REPORTING_WEIGHT[s] for s in states], dtype=float)
    state_w /= state_w.sum()
    diseases = list(DISEASES)
    base_w = np.array([DISEASES[d][1] for d in diseases], dtype=float)

    rows = []
    for year in range(start_year, end_year + 1):
        n = rows_per_year
        for _ in range(n):
            state = rng.choice(states, p=state_w)
            mult = np.array([state_disease_multiplier(state, d, DISEASES[d][0]) for d in diseases])
            w = base_w * mult
            disease = rng.choice(diseases, p=w / w.sum())
            month = int(rng.choice(12, p=DISEASES[disease][6])) + 1
            day_max = (date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)).day
            start = date(year, month, int(rng.integers(1, day_max + 1)))
            lag = int(rng.choice([0, 0, 0, 1, 1, 2, 3]))
            report = start + timedelta(days=lag)
            if report > last_date:
                continue
            cases, deaths = draw_cases_deaths(rng, disease)
            iso = report.isocalendar()
            age_days = (last_date - report).days
            names, probs = STATUS_RECENT if age_days < 45 else STATUS_OLDER
            rows.append({
                "year": iso[0],
                "week": iso[1],
                "outbreak_starting_date": start,
                "reporting_date": report,
                "state": state,
                "district_as_per_lgd": rng.choice(STATE_DISTRICTS[state]),
                "disease_illness_name": disease,
                "status": rng.choice(names, p=probs),
                "cases": cases,
                "deaths": deaths,
            })
    return pd.DataFrame(rows)


def drop_missing_weeks(rng, df, frac=0.08):
    """Real data has weeks with no/late reports; mimic that so 'no data' != 'no outbreak'."""
    weeks = df[["year", "week"]].drop_duplicates()
    drop = weeks.sample(frac=frac, random_state=int(rng.integers(0, 1_000_000)))
    key = df["year"].astype(str) + "-" + df["week"].astype(str)
    dkey = drop["year"].astype(str) + "-" + drop["week"].astype(str)
    return df[~key.isin(set(dkey))].copy()


def plant_anomalies(rng, df, n_clusters, n_mega, last_date):
    """Add surge clusters + single mega-outbreaks. Returns (new_df, ground_truth_df)."""
    truth = []
    extra = []
    candidates = ["Dengue", "Acute Diarrheal Disease", "Cholera", "Malaria", "Measles", "Viral Hepatitis"]
    big_states = [s for s, w in STATE_REPORTING_WEIGHT.items() if w >= 2.0]
    for i in range(n_clusters):
        state = str(rng.choice(big_states))
        disease = str(rng.choice(candidates))
        year = int(rng.integers(2012, 2025))
        season = DISEASES[disease][6]
        month = int(rng.choice(12, p=season)) + 1
        k = int(rng.integers(14, 26))
        for _ in range(k):
            start = date(year, month, int(rng.integers(1, 28)))
            report = start + timedelta(days=int(rng.integers(0, 3)))
            cases, deaths = draw_cases_deaths(rng, disease, scale=4.0)
            iso = report.isocalendar()
            extra.append({
                "year": iso[0], "week": iso[1],
                "outbreak_starting_date": start, "reporting_date": report,
                "state": state, "district_as_per_lgd": rng.choice(STATE_DISTRICTS[state]),
                "disease_illness_name": disease, "status": "Closed",
                "cases": cases, "deaths": deaths,
            })
        truth.append({"type": "surge_cluster", "state": state, "disease": disease,
                      "year": year, "month": month, "extra_rows": k})
    for i in range(n_mega):
        state = str(rng.choice(list(STATE_DISTRICTS)))
        disease = str(rng.choice(["Acute Diarrheal Disease", "Suspected Food Poisoning", "Cholera", "Dengue", "Viral Fever"]))
        year = int(rng.integers(2010, 2026))
        month = int(rng.choice(12, p=DISEASES[disease][6])) + 1
        start = date(year, month, int(rng.integers(1, 28)))
        report = start + timedelta(days=1)
        if report > last_date:
            continue
        cases = int(rng.integers(350, 900))
        deaths = int(rng.integers(0, 6))
        iso = report.isocalendar()
        extra.append({
            "year": iso[0], "week": iso[1],
            "outbreak_starting_date": start, "reporting_date": report,
            "state": state, "district_as_per_lgd": rng.choice(STATE_DISTRICTS[state]),
            "disease_illness_name": disease, "status": "Closed",
            "cases": cases, "deaths": deaths,
        })
        truth.append({"type": "mega_outbreak", "state": state, "disease": disease,
                      "year": year, "month": month, "cases": cases, "deaths": deaths})
    return pd.concat([df, pd.DataFrame(extra)], ignore_index=True), pd.DataFrame(truth)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--start-year", type=int, default=2009)
    ap.add_argument("--end-year", type=int, default=2026)
    ap.add_argument("--rows-per-year", type=int, default=2100)
    ap.add_argument("--last-date", default="2026-03-29", help="no reports after this date (YYYY-MM-DD)")
    ap.add_argument("--clusters", type=int, default=6)
    ap.add_argument("--mega", type=int, default=20)
    ap.add_argument("--out", default=".", help="output folder")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    last_date = date.fromisoformat(args.last_date)

    df = build_rows(rng, args.start_year, args.end_year, args.rows_per_year, last_date)
    df = drop_missing_weeks(rng, df)
    df, truth = plant_anomalies(rng, df, args.clusters, args.mega, last_date)

    df["units"] = "cases in absolute number, deaths in absolute number"
    df["source"] = "synthetic"
    df = df.sort_values("reporting_date", ascending=False).reset_index(drop=True)
    for c in ("outbreak_starting_date", "reporting_date"):
        df[c] = pd.to_datetime(df[c]).dt.strftime("%d-%m-%Y")  # same dd-mm-yyyy as the source

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "synthetic_idsp_outbreaks.csv", index=False)
    truth.to_csv(out / "synthetic_planted_anomalies.csv", index=False)
    print(f"Wrote {len(df):,} rows -> {out / 'synthetic_idsp_outbreaks.csv'}")
    print(f"Wrote {len(truth)} planted anomalies -> {out / 'synthetic_planted_anomalies.csv'}")


if __name__ == "__main__":
    main()
