"""
Travel Health & Safety engine (historical analysis only - NOT a prediction or a "you are safe" score).

Loads historical outbreak reports once at process start and precomputes:

  1. Seasonal pattern   - outbreaks by calendar month, per state and disease group
  2. Anomaly detection  - Isolation Forest, two views:
        a) state-month   : "this month had unusually HIGH outbreak activity for this state"
        b) single outbreak: "this outbreak was unusually large for its disease"
  3. Clustering         - K-Means over per-state disease profiles ("states with similar patterns")

and exposes `get_state_profile(state, travel_month)` for the API layer.

Data: data/idsp_outbreaks.csv, same columns as the IDSP weekly-outbreak dataset
(year, week, outbreak_starting_date, reporting_date, state, district_as_per_lgd,
disease_illness_name, status, cases, deaths, units, source). The `source` column is
passed through to the API so the UI can show a "demo data" label when rows are synthetic.
Swapping in real data later only needs the same column names - no code change.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

APP_DIR = Path(__file__).resolve().parent.parent  # app/services -> app/
DATA_PATH = APP_DIR / "data" / "idsp_outbreaks.csv"

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

GROUP_LABELS = {
    "gi": "Water & food-borne",
    "vector": "Mosquito-borne",
    "vpd": "Vaccine-preventable & rash",
    "resp": "Respiratory & fever",
    "zoonotic": "Animal-linked",
    "other": "Other",
}
GROUPS = list(GROUP_LABELS)

# General public-health travel advice per group (static rules, NOT ML output).
PRECAUTIONS = {
    "gi": ["Drink bottled or boiled water and avoid ice of unknown source",
           "Eat freshly cooked, hot food; be careful with raw salads and street food",
           "Carry oral rehydration salts (ORS) and wash hands before eating"],
    "vector": ["Use mosquito repellent and sleep under a net or in a screened room",
               "Wear long sleeves and trousers around dawn and dusk",
               "Avoid places with stagnant water"],
    "vpd": ["Check your routine vaccines (such as MMR and chickenpox) are up to date before travel",
            "Avoid close contact with anyone showing a fever with rash"],
    "resp": ["Carry a mask for crowded places and wash hands often",
             "Stay home and rest if you develop fever or cough on the trip"],
    "zoonotic": ["Avoid contact with stray animals and do not wade through floodwater",
                 "After any animal bite or scratch, wash the wound and seek medical care right away"],
    "other": ["Check local health guidance before you travel"],
}

OFFICIAL_SOURCES = ["Integrated Disease Surveillance Programme (IDSP), NCDC",
                    "Ministry of Health and Family Welfare (MoHFW)"]

# "Learn more" links per disease group (WHO fact sheets). The tips above are general public-health
# advice; these pages are where a reader can check the detail. Open every link and read the page
# before you cite it in your report - links change.
_WHO = "https://www.who.int/news-room/fact-sheets/detail/"
PRECAUTION_SOURCES = {
    "gi": [{"name": "WHO: Diarrhoeal disease", "url": _WHO + "diarrhoeal-disease"},
           {"name": "WHO: Cholera", "url": _WHO + "cholera"},
           {"name": "WHO: Food safety", "url": _WHO + "food-safety"}],
    "vector": [{"name": "WHO: Dengue and severe dengue", "url": _WHO + "dengue-and-severe-dengue"},
               {"name": "WHO: Malaria", "url": _WHO + "malaria"}],
    "vpd": [{"name": "WHO: Measles", "url": _WHO + "measles"}],
    "resp": [{"name": "WHO: Influenza (seasonal)", "url": _WHO + "influenza-(seasonal)"}],
    "zoonotic": [{"name": "WHO: Rabies", "url": _WHO + "rabies"}],
    "other": [],
}

# Keyword -> group. Order matters ("fever with rash" must hit vpd before the generic "fever").
# Keyword matching (not an exact-name list) so a real dataset with ~240 disease names still works.
_KEYWORDS = [
    ("vpd", ["rash", "measles", "rubella", "mumps", "chickenpox", "varicella", "diphtheria",
             "pertussis", "polio", "tetanus"]),
    ("gi", ["diarrh", "gastro", "food poison", "dysentery", "cholera", "hepatitis", "enteric",
            "typhoid", "jaundice", "shigell", "rotavirus"]),
    ("vector", ["dengue", "chikungunya", "malaria", "encephalitis", "kala", "zika", "scrub typhus"]),
    ("zoonotic", ["rabies", "leptospir", "anthrax", "cchf", "crimean", "brucell", "nipah", "plague"]),
    ("resp", ["influenza", "h1n1", "viral fever", "fever", "respiratory", "covid", "pneumonia"]),
]


def classify_disease(name: str) -> str:
    n = str(name).lower()
    for group, words in _KEYWORDS:
        if any(w in n for w in words):
            return group
    return "other"


# ---------------------------------------------------------------------------
# Load + clean
# ---------------------------------------------------------------------------
def _load() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    required = ["state", "disease_illness_name", "cases", "deaths", "outbreak_starting_date"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{DATA_PATH.name} is missing required columns: {missing}")

    start = pd.to_datetime(df["outbreak_starting_date"], format="%d-%m-%Y", errors="coerce")
    if "reporting_date" in df.columns:
        start = start.fillna(pd.to_datetime(df["reporting_date"], format="%d-%m-%Y", errors="coerce"))
    df["start"] = start
    df = df.dropna(subset=["start", "state", "disease_illness_name"]).copy()
    df["cases"] = pd.to_numeric(df["cases"], errors="coerce").fillna(0).clip(lower=0)
    df["deaths"] = pd.to_numeric(df["deaths"], errors="coerce").fillna(0).clip(lower=0)
    df["cal_year"] = df["start"].dt.year
    df["month"] = df["start"].dt.month
    df["group"] = df["disease_illness_name"].map(classify_disease)
    if "source" not in df.columns:
        df["source"] = "unspecified"
    if "district_as_per_lgd" in df.columns:
        df["district"] = df["district_as_per_lgd"]
    elif "district_as_per_source" in df.columns:
        df["district"] = df["district_as_per_source"]
    else:
        df["district"] = ""
    return df.reset_index(drop=True)


DF = _load()
DATA_THROUGH = DF["start"].max()
LAST_YEAR = int(DF["cal_year"].max())
IS_SYNTHETIC = bool(DF["source"].astype(str).str.lower().eq("synthetic").any())
DATA_SOURCES = sorted(DF["source"].astype(str).unique().tolist())


# ---------------------------------------------------------------------------
# 1. Anomaly detection (Isolation Forest)
# ---------------------------------------------------------------------------
def _state_month_anomalies() -> pd.DataFrame:
    sm = (DF.groupby(["state", "cal_year", "month"])
            .agg(outbreaks=("cases", "size"), cases=("cases", "sum"), deaths=("deaths", "sum"))
            .reset_index())
    baseline = sm.groupby(["state", "month"])["outbreaks"].transform("median").clip(lower=1)
    sm["rel"] = sm["outbreaks"] / baseline
    X = np.column_stack([np.log1p(sm["outbreaks"]), np.log1p(sm["cases"]),
                         np.log1p(sm["deaths"]), np.log1p(sm["rel"])])
    model = IsolationForest(n_estimators=200, contamination=0.02, random_state=42).fit(X)
    sm["score"] = -model.score_samples(X)           # higher = more unusual
    sm["flag"] = (model.predict(X) == -1) & (sm["rel"] >= 1.5)   # only unusually HIGH months
    # which disease drove the month?
    top = (DF.groupby(["state", "cal_year", "month", "disease_illness_name"])["cases"].sum()
             .reset_index().sort_values("cases", ascending=False)
             .drop_duplicates(["state", "cal_year", "month"])
             .rename(columns={"disease_illness_name": "top_disease"})
             [["state", "cal_year", "month", "top_disease"]])
    return sm.merge(top, on=["state", "cal_year", "month"], how="left")


def _outbreak_anomalies() -> pd.DataFrame:
    d = DF.copy()
    med = d.groupby("disease_illness_name")["cases"].transform("median")
    d["size_rel"] = np.log1p(d["cases"]) - np.log1p(med)
    cfr = d["deaths"] / d["cases"].clip(lower=1)
    d["cfr_rel"] = cfr - cfr.groupby(d["disease_illness_name"]).transform("mean")
    X = np.column_stack([d["size_rel"], np.log1p(d["deaths"]), d["cfr_rel"]])
    model = IsolationForest(n_estimators=200, contamination=0.01, random_state=42).fit(X)
    d["score"] = -model.score_samples(X)
    d["flag"] = (model.predict(X) == -1) & (d["size_rel"] > 0.5)   # only unusually LARGE outbreaks
    return d


SM = _state_month_anomalies()
OB = _outbreak_anomalies()


# ---------------------------------------------------------------------------
# 2. Seasonal pattern
# ---------------------------------------------------------------------------
_SEASON_COUNTS = (DF.groupby(["state", "group", "month"]).size()
                    .unstack(fill_value=0).reindex(columns=range(1, 13), fill_value=0))
MIN_GROUP_REPORTS = 30   # below this, a seasonal shape is mostly noise


def _season_for(state: str, group: str):
    try:
        row = _SEASON_COUNTS.loc[(state, group)]
    except KeyError:
        return None
    total = int(row.sum())
    if total < MIN_GROUP_REPORTS:
        return None
    share = (row / total).to_numpy()
    peaks = [m + 1 for m in np.argsort(-share)[:4] if share[m] >= 0.115]
    if not peaks:
        peaks = [int(np.argmax(share)) + 1]
    return {"total": total, "share": share, "peaks": sorted(peaks)}


# ---------------------------------------------------------------------------
# 3. K-Means over state disease profiles
# ---------------------------------------------------------------------------
MIN_STATE_REPORTS = 100


def _build_clusters():
    counts = DF.groupby("state").size()
    states = counts[counts >= MIN_STATE_REPORTS].index.tolist()
    if len(states) < 8:
        return {}, {}
    rows = []
    for s in states:
        sub = DF[DF["state"] == s]
        share = sub["group"].value_counts(normalize=True).reindex(GROUPS, fill_value=0)
        peak_m = int(sub["month"].value_counts().idxmax())
        rows.append(list(share.values) + [
            np.log1p(sub["cases"].mean()),
            np.log1p(1000 * sub["deaths"].sum() / max(sub["cases"].sum(), 1)),
            np.sin(2 * np.pi * peak_m / 12), np.cos(2 * np.pi * peak_m / 12),
        ])
    Z = StandardScaler().fit_transform(np.array(rows))
    k = 4 if len(states) >= 16 else 3
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Z)

    names, used = {}, set()
    for c in range(k):
        cz = km.cluster_centers_[c][:len(GROUPS)]
        order = np.argsort(-cz)
        label = f"{GROUP_LABELS[GROUPS[order[0]]]}-heavy"
        if cz[order[1]] > 0.4:
            label = f"{GROUP_LABELS[GROUPS[order[0]]]} + {GROUP_LABELS[GROUPS[order[1]]].lower()}"
        if label in used:
            label = f"{label} (group {c + 1})"
        used.add(label)
        names[c] = label
    return dict(zip(states, km.labels_.tolist())), names


STATE_CLUSTER, CLUSTER_NAMES = _build_clusters()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _fmt_date(ts) -> str:
    return pd.Timestamp(ts).strftime("%d %b %Y")


def get_state_profile(state: str, travel_month: int | None = None) -> dict:
    sub = DF[DF["state"] == state]
    base = {
        "state": state,
        "is_synthetic": IS_SYNTHETIC,
        "data_sources": DATA_SOURCES,
        "official_sources": OFFICIAL_SOURCES,
        "current_alerts": {
            "connected": False,
            "message": "Live outbreak alerts are not connected yet. Check official sources before you travel.",
        },
    }
    caveats = [
        "These are outbreaks that were officially reported. Reporting varies between states and weeks, "
        "so no reports does not mean no risk.",
        "This is a historical summary, not a prediction. It is general information, not medical advice.",
    ]
    if IS_SYNTHETIC:
        caveats.insert(0, "DEMO DATA: this dataset is synthetic and does not describe real outbreaks.")

    if sub.empty:
        return {**base, "has_data": False, "caveats": caveats,
                "message": "No outbreak reports for this state in our data. That does not mean there are none."}

    # --- disease mix ---
    mix = sub["group"].value_counts()
    disease_mix = [{"group": g, "label": GROUP_LABELS[g], "outbreaks": int(n),
                    "share": round(float(n) / len(sub), 3)} for g, n in mix.items()]
    top_diseases = sub["disease_illness_name"].value_counts().head(5)

    # --- yearly activity ---
    yearly = (sub.groupby("cal_year").agg(outbreaks=("cases", "size"), cases=("cases", "sum"),
                                          deaths=("deaths", "sum")).reset_index())
    yearly_out = [{"year": int(r.cal_year), "outbreaks": int(r.outbreaks), "cases": int(r.cases),
                   "deaths": int(r.deaths),
                   "partial": bool(r.cal_year == LAST_YEAR and DATA_THROUGH.month < 12)}
                  for r in yearly.itertuples()]
    full_years = yearly[yearly["cal_year"] < LAST_YEAR] if len(yearly) > 1 else yearly
    peak_year = int(full_years.loc[full_years["outbreaks"].idxmax(), "cal_year"])

    # --- seasonality ---
    seasonal, elevated = [], []
    for g in GROUPS:
        s = _season_for(state, g)
        if not s:
            continue
        seasonal.append({"group": g, "label": GROUP_LABELS[g], "total": s["total"],
                         "monthly_share": [round(float(x), 4) for x in s["share"]],
                         "peak_months": [MONTH_NAMES[m - 1] for m in s["peaks"]]})
        if travel_month:
            ratio = float(s["share"][travel_month - 1]) * 12
            if ratio >= 1.4:
                elevated.append({"group": g, "label": GROUP_LABELS[g], "ratio": round(ratio, 1),
                                 "precautions": PRECAUTIONS[g], "sources": PRECAUTION_SOURCES[g]})
    elevated.sort(key=lambda x: -x["ratio"])

    # --- ML: unusual months + notable outbreaks ---
    sm = SM[(SM["state"] == state) & SM["flag"]].sort_values("score", ascending=False).head(5)
    unusual_months = [{"year": int(r.cal_year), "month": MONTH_NAMES[int(r.month) - 1],
                       "outbreaks": int(r.outbreaks), "cases": int(r.cases),
                       "times_normal": round(float(r.rel), 1), "top_disease": r.top_disease}
                      for r in sm.itertuples()]
    ob = OB[(OB["state"] == state) & OB["flag"]].sort_values("score", ascending=False).head(5)
    notable = [{"disease": r.disease_illness_name, "district": r.district,
                "date": _fmt_date(r.start), "cases": int(r.cases), "deaths": int(r.deaths)}
               for r in ob.itertuples()]

    # --- ML: cluster ---
    cluster = None
    if state in STATE_CLUSTER:
        cid = STATE_CLUSTER[state]
        similar = [s for s, c in STATE_CLUSTER.items() if c == cid and s != state]
        cluster = {"label": CLUSTER_NAMES[cid], "similar_states": sorted(similar)[:8]}

    # --- precautions (static, for the state's biggest groups) ---
    top_groups = [g for g in mix.index[:3] if g != "other"]
    precautions = [{"group": g, "label": GROUP_LABELS[g], "tips": PRECAUTIONS[g],
                    "sources": PRECAUTION_SOURCES[g]} for g in top_groups]

    return {
        **base,
        "has_data": True,
        "total_outbreaks": int(len(sub)),
        "years_covered": [int(sub["cal_year"].min()), int(sub["cal_year"].max())],
        "data_through": _fmt_date(DATA_THROUGH),
        "disease_mix": disease_mix,
        "top_diseases": [{"disease": d, "outbreaks": int(n)} for d, n in top_diseases.items()],
        "yearly": yearly_out,
        "peak_year": peak_year,
        "seasonal": seasonal,
        "travel_month": (MONTH_NAMES[travel_month - 1] if travel_month else None),
        "elevated_for_month": elevated,
        "unusual_months": unusual_months,
        "notable_outbreaks": notable,
        "cluster": cluster,
        "precautions": precautions,
        "caveats": caveats,
    }
