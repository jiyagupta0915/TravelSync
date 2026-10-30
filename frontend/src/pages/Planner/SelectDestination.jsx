import { useEffect, useRef, useState } from "react";
import { ArrowRight, Check, MapPin, Search, Sparkles } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Navbar from "../../components/Navbar/Navbar";
import Footer from "../../components/Footer/Footer";
import TopPlaces from "../../components/TopPlaces/TopPlaces";
import { searchDestinations } from "../../services/recommendationApi";
import NumberField from "../../components/NumberField/NumberField";
import { createTrip } from "../../services/tripApi";
import { isAbort } from "../../services/apiClient";
import { useAuth } from "../../context/useAuth";
import { MAX_BUDGET_INR, MAX_DURATION_DAYS } from "../../utils/limits";
import { parsePositiveInteger } from "../../utils/numberField";
import "./Planner.css";

export default function SelectDestination() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(() => (searchParams.get("q") || "").slice(0, 100));   // from the top-bar search
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [duration, setDuration] = useState(() => String(user?.settings?.default_duration_days || 5));
  const [budget, setBudget] = useState(() => String(user?.settings?.default_budget_inr || 20000));
  const [fieldErrors, setFieldErrors] = useState({});
  const durationRef = useRef(null);
  const budgetRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      if (!query.trim()) { setResults([]); return; }
      setSearching(true);
      try { const data = await searchDestinations(query, controller.signal); setResults(data.results || []); }
      catch (err) { if (!isAbort(err)) setResults([]); }
      finally { if (!controller.signal.aborted) setSearching(false); }
    }, 220);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query]);

  async function handleContinue() {
    if (loading) return;
    if (!selected) { setError("Choose a destination from the suggestions first."); return; }
    const days = parsePositiveInteger(duration, { label: "the trip duration", max: MAX_DURATION_DAYS, unit: " days" });
    const money = parsePositiveInteger(budget, { label: "your budget", max: MAX_BUDGET_INR });
    const errors = { ...(days.ok ? {} : { duration: days.error }), ...(money.ok ? {} : { budget: money.error }) };
    setFieldErrors(errors);
    if (errors.duration || errors.budget) { setError(""); (errors.duration ? durationRef : budgetRef).current?.focus(); return; }
    setError(""); setLoading(true);
    try {
      await createTrip({ destination:selected.Destination, duration:days.value, budget:money.value, source:"known-destination" });
      navigate("/home");
    } catch (err) { setError(err.message || "Could not save this trip."); }
    finally { setLoading(false); }
  }

  return (
    <div className="known-page">
      <Navbar />
      <main className="known-main">
        <section className="known-hero">
          <div>
            <span className="known-eyebrow"><Sparkles size={15}/> I KNOW MY DESTINATION</span>
            <h1>Start with the <span>place.</span></h1>
            <p>You already know where you want to go. Choose it here and TravelSync will create your trip space so the rest of your travel tools can build around it.</p>
          </div>
          <div className="known-hero-card"><MapPin size={25}/><strong>One destination.</strong><span>Everything else can follow.</span></div>
        </section>

        <section className="known-card">
          <div className="known-card__heading"><div><span className="section-kicker">DESTINATION</span><h2>Where are you going?</h2></div><span className="known-step">01</span></div>
          <div className="known-search"><Search size={19}/><input autoFocus aria-label="Search for a destination" value={query} onChange={(e) => { setQuery(e.target.value); setSelected(null); setError(""); }} placeholder="Search for a destination, city or state" /></div>
          {query && !selected && <div className="known-results">{searching ? <div className="known-message">Searching destinations…</div> : results.length ? results.map((item) => <button type="button" key={`${item.Destination}-${item.State}`} onClick={() => { setSelected(item); setQuery(item.Destination); setResults([]); }}><MapPin size={16}/><span><strong>{item.Destination}</strong><small>{item.State} · {item.Region}</small></span></button>) : <div className="known-message">No matching destination found.</div>}</div>}

          {selected && <div className="selected-destination"><div><div className="selected-destination__title"><Check size={17}/> {selected.Destination}</div><p>{selected.State} · {selected.Region}</p></div><button type="button" onClick={() => { setSelected(null); setQuery(""); }}>Change</button></div>}

          {selected && <TopPlaces destination={selected.Destination} />}

          <div className="known-details">
            <label><span>Trip duration</span><div className="known-input"><input ref={durationRef} type="number" min="1" max="30" value={duration} onChange={(e) => { setDuration(e.target.value); setFieldErrors((c) => ({ ...c, duration: undefined })); }} aria-invalid={Boolean(fieldErrors.duration) || undefined}/><b>days</b></div>{fieldErrors.duration && <small className="known-field-error" role="alert">{fieldErrors.duration}</small>}</label>
            <label><span>Total budget</span><div className="known-input"><b>₹</b><NumberField inputRef={budgetRef} value={budget} maxLength={8} onChange={(v) => { setBudget(v); setFieldErrors((c) => ({ ...c, budget: undefined })); }} invalid={Boolean(fieldErrors.budget)} ariaLabel="Total budget in rupees"/></div>{fieldErrors.budget && <small className="known-field-error" role="alert">{fieldErrors.budget}</small>}</label>
          </div>
          {error && <p className="known-error" role="alert">{error}</p>}
          <button className="known-continue" type="button" onClick={handleContinue} disabled={loading}>{loading ? "Saving trip…" : <>Continue with {selected?.Destination || "destination"}<ArrowRight size={18}/></>}</button>
          <button className="known-alternate" type="button" onClick={() => navigate("/planner/recommend")}>Not sure where to go? Get recommendations instead</button>
        </section>
      </main>
      <Footer />
    </div>
  );
}
