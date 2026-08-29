import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Check, Compass, MapPin, RotateCcw, Search, Sparkles, Users, SlidersHorizontal } from "lucide-react";
import Navbar from "../../components/Navbar/Navbar";
import Footer from "../../components/Footer/Footer";
import { getFeatures, recommendDestinations, searchStartingLocations } from "../../services/recommendationApi";
import { createTrip } from "../../services/tripApi";
import { useNavigate } from "react-router-dom";
import "./RecommendDestination.css";

const IMPORTANCE = { "Must have": 3, "Nice to have": 2, Optional: 1 };
const TRAVELLER_TYPES = [
  { value: "Solo", label: "Solo", description: "Just me", icon: "🧳" },
  { value: "Couple", label: "Couple", description: "Two travellers", icon: "🫶" },
  { value: "Friends", label: "Friends", description: "A group of friends", icon: "👯" },
  { value: "Family", label: "Family", description: "Family trip", icon: "👨‍👩‍👧" },
];
const DEFAULT_FEATURES = ["Mountain","Beach","Nature","Adventure","Culture","Relaxation","Nightlife","Spiritual","Trekking","Photography","Food","Heritage"];
const FEATURE_ICONS = { Mountain:"⛰️", Beach:"🏖️", Nature:"🌿", Adventure:"🧗", Culture:"🏛️", Relaxation:"🧘", Nightlife:"🌙", Spiritual:"🛕", Trekking:"🥾", Photography:"📷", Food:"🍜", Heritage:"🏰" };

export default function RecommendDestination() {
  const navigate = useNavigate();
  const [features, setFeatures] = useState(DEFAULT_FEATURES);
  const [travellerTypes, setTravellerTypes] = useState(TRAVELLER_TYPES.map((item) => item.value));
  const [travellerType, setTravellerType] = useState("Friends");
  const [selectedFeatures, setSelectedFeatures] = useState(["Mountain", "Nature", "Adventure"]);
  const [importance, setImportance] = useState({ Mountain:"Must have", Nature:"Nice to have", Adventure:"Must have" });
  const [duration, setDuration] = useState(5);
  const [budget, setBudget] = useState(20000);
  const [startQuery, setStartQuery] = useState("");
  const [startingLocations, setStartingLocations] = useState([]);
  const [startLocation, setStartLocation] = useState(null);
  const [maxDistance, setMaxDistance] = useState(2000);
  const [results, setResults] = useState([]);
  const [rules, setRules] = useState(null);
  const [loading, setLoading] = useState(false);
  const [locationsLoading, setLocationsLoading] = useState(false);
  const [savingDestination, setSavingDestination] = useState("");
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    getFeatures().then((data) => {
      if (data.interest_features?.length) setFeatures(data.interest_features);
      if (data.traveller_types?.length) {
        setTravellerTypes(data.traveller_types);
        setTravellerType((current) => data.traveller_types.includes(current) ? current : data.traveller_types[0]);
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!startQuery.trim()) { setStartingLocations([]); return; }
      setLocationsLoading(true);
      try {
        const data = await searchStartingLocations(startQuery);
        setStartingLocations(data.results || []);
      } catch { setStartingLocations([]); }
      finally { setLocationsLoading(false); }
    }, 220);
    return () => clearTimeout(timer);
  }, [startQuery]);

  const selectedRows = useMemo(() => selectedFeatures.map((feature) => ({ feature, level: importance[feature] || "Nice to have" })), [selectedFeatures, importance]);

  function toggleFeature(feature) {
    setError("");
    setSelectedFeatures((current) => {
      if (current.includes(feature)) {
        setImportance((old) => { const copy = { ...old }; delete copy[feature]; return copy; });
        return current.filter((item) => item !== feature);
      }
      if (current.length >= 5) { setError("Choose up to 5 interests to keep the recommendation focused."); return current; }
      setImportance((old) => ({ ...old, [feature]: "Nice to have" }));
      return [...current, feature];
    });
  }

  function resetForm() {
    setTravellerType("Friends"); setSelectedFeatures(["Mountain","Nature","Adventure"]); setImportance({ Mountain:"Must have", Nature:"Nice to have", Adventure:"Must have" });
    setDuration(5); setBudget(20000); setStartQuery(""); setStartLocation(null); setMaxDistance(2000); setResults([]); setRules(null); setError(""); setSearched(false);
  }

  async function handleSubmit(event) {
    event.preventDefault(); setError(""); setSearched(true);
    if (!selectedFeatures.length) return setError("Select at least one travel interest.");
    if (!startLocation) return setError("Select your starting location from the suggestions so distance can be calculated.");
    if (Number(budget) <= 0 || Number(duration) <= 0 || Number(maxDistance) <= 0) return setError("Enter valid duration, budget and distance values.");

    const preferences = Object.fromEntries(features.map((feature) => [feature, selectedFeatures.includes(feature) ? 1 : 0]));
    const importancePayload = Object.fromEntries(features.map((feature) => [feature, selectedFeatures.includes(feature) ? IMPORTANCE[importance[feature] || "Nice to have"] : 0]));
    setLoading(true);
    try {
      const data = await recommendDestinations({ preferences, importance: importancePayload, traveller_type: travellerType, duration:Number(duration), budget:Number(budget), start_lat:Number(startLocation.Latitude), start_lon:Number(startLocation.Longitude), max_distance_km:Number(maxDistance), top_n:6 });
      setResults(data.recommendations || []); setRules(data.rules || null);
      if (!data.recommendations?.length) setError("No destination matched those constraints. Try widening your distance or budget.");
    } catch (err) { setResults([]); setError(err.message || "Something went wrong while finding destinations."); }
    finally { setLoading(false); }
  }

  async function chooseDestination(result) {
    setSavingDestination(result.Destination); setError("");
    try {
      await createTrip({ destination: result.Destination, duration:Number(duration), budget:Number(budget), traveller_type:travellerType, source:"recommendation" });
      navigate("/home");
    } catch (err) { setError(err.message || "Could not save this trip."); setSavingDestination(""); }
  }

  return (
    <div className="recommend-page">
      <Navbar />
      <main>
        <section className="recommend-hero">
          <div className="recommend-hero__copy">
            <div className="eyebrow"><Sparkles size={15} /> PERSONALIZED DESTINATION DISCOVERY</div>
            <h1>Find a place that <span>fits your trip.</span></h1>
            <p>Tell TravelSync what matters to you. Your preferences are matched with destination profiles, then checked against duration, budget and geographical distance.</p>
            <div className="hero-rule"><span>Preferences</span><i /> <span>Trip constraints</span><i /> <span>Ranked matches</span></div>
          </div>
          <div className="recommend-hero__visual" aria-hidden="true"><div className="visual-orbit visual-orbit--one" /><div className="visual-orbit visual-orbit--two" /><div className="visual-pin"><MapPin size={27} /></div><div className="visual-card visual-card--top"><Compass size={17} /> Preference match</div><div className="visual-card visual-card--bottom"><Check size={17} /> Distance checked</div></div>
        </section>

        <section className="planner-shell">
          <form className="recommend-form" onSubmit={handleSubmit}>
            <div className="form-heading"><div><span className="section-kicker">YOUR TRIP</span><h2>Tell us what you're looking for</h2><p>Choose the preferences that should influence your recommendations.</p></div><button type="button" className="reset-button" onClick={resetForm}><RotateCcw size={15} /> Reset</button></div>

            <div className="form-section">
              <div className="section-title-row"><div><span className="section-kicker">01 · TRAVELLERS</span><h3>Who are you travelling with?</h3></div><Users size={19} /></div>
              <div className="traveller-grid">{travellerTypes.map((type) => { const item = TRAVELLER_TYPES.find((entry) => entry.value === type) || { value:type,label:type,description:"Travel style",icon:"✦" }; return <button key={type} type="button" className={`traveller-card ${travellerType === type ? "is-selected" : ""}`} onClick={() => setTravellerType(type)}><span className="traveller-card__icon">{item.icon}</span><span><strong>{item.label}</strong><small>{item.description}</small></span>{travellerType === type && <Check size={17} />}</button>; })}</div>
            </div>

            <div className="form-section">
              <div className="section-title-row"><div><span className="section-kicker">02 · INTERESTS</span><h3>What kind of trip do you want?</h3></div><span className="selection-count">{selectedFeatures.length}/5 selected</span></div>
              <div className="interest-grid">{features.map((feature) => <button key={feature} type="button" className={`interest-chip ${selectedFeatures.includes(feature) ? "is-selected" : ""}`} onClick={() => toggleFeature(feature)}><span>{FEATURE_ICONS[feature] || "✦"}</span>{feature}</button>)}</div>
            </div>

            <div className="form-section">
              <div className="section-title-row"><div><span className="section-kicker">03 · PRIORITIES</span><h3>How important are those interests?</h3></div><SlidersHorizontal size={19} /></div>
              <div className="priority-list">{selectedRows.length ? selectedRows.map(({ feature, level }) => <div className="priority-row" key={feature}><div className="priority-name"><span>{FEATURE_ICONS[feature] || "✦"}</span>{feature}</div><select value={level} onChange={(e) => setImportance((current) => ({ ...current, [feature]: e.target.value }))}><option>Must have</option><option>Nice to have</option><option>Optional</option></select></div>) : <p className="muted-copy">Select at least one interest above.</p>}</div>
            </div>

            <div className="form-section">
              <div className="section-title-row"><div><span className="section-kicker">04 · TRIP CONSTRAINTS</span><h3>Set your travel boundaries</h3></div></div>
              <div className="constraints-grid">
                <label className="field"><span>Starting location</span><div className="location-search"><Search size={17} /><input value={startQuery} onChange={(e) => { setStartQuery(e.target.value); setStartLocation(null); }} placeholder="Search a city or state" /></div>{startQuery && !startLocation && <div className="location-results">{locationsLoading ? <div className="location-message">Searching locations…</div> : startingLocations.length ? startingLocations.map((location) => <button type="button" key={`${location.Location}-${location.State}`} onClick={() => { setStartLocation(location); setStartQuery(location.Location); }}><MapPin size={15} /><span><strong>{location.Location}</strong><small>{location.State}</small></span></button>) : <div className="location-message">No starting locations found.</div>}</div>}{startLocation && <div className="selected-location"><Check size={14} /> {startLocation.Location}, {startLocation.State}</div>}</label>
                <label className="field"><span>Maximum travel distance</span><div className="input-with-unit"><input type="number" min="1" max="10000" value={maxDistance} onChange={(e) => setMaxDistance(e.target.value)} /><b>km</b></div><small>Calculated from your starting point using destination coordinates.</small></label>
                <label className="field"><span>Trip duration</span><div className="input-with-unit"><input type="number" min="1" max="30" value={duration} onChange={(e) => setDuration(e.target.value)} /><b>days</b></div><small>Destinations within ±1 day receive the strongest duration score.</small></label>
                <label className="field"><span>Total budget</span><div className="input-with-unit"><b>₹</b><input type="number" min="1" value={budget} onChange={(e) => setBudget(e.target.value)} /></div><small>Nearby costs remain eligible instead of requiring an exact match.</small></label>
              </div>
            </div>

            {error && <div className="form-error" role="alert">{error}</div>}
            <button className="find-button" type="submit" disabled={loading}>{loading ? <><span className="spinner" /> Finding matches…</> : <>Find my destinations <ArrowRight size={19} /></>}</button>
          </form>

          <aside className="recommend-side">
            <div className="side-note"><div className="side-note__icon"><Compass size={20} /></div><span className="section-kicker">HOW IT WORKS</span><h3>Three checks shape the ranking.</h3><p>TravelSync first finds destinations with similar preference profiles. Then the backend checks the practical constraints you entered.</p><div className="side-note__steps"><div><span>01</span><p>Preference similarity</p></div><div><span>02</span><p>Duration + budget fit</p></div><div><span>03</span><p>Geographical distance</p></div></div></div>
            <div className="side-tip"><MapPin size={17} /><div><strong>Why your starting point matters</strong><p>We use its latitude and longitude to calculate the distance to every candidate destination.</p></div></div>
          </aside>
        </section>

        <section className="results-section">
          <div className="results-header"><div><span className="section-kicker">YOUR MATCHES</span><h2>{results.length ? "Destinations worth considering" : searched ? "No suitable matches yet" : "Your recommendations will appear here"}</h2><p>{results.length ? "Choose a destination to save it to your TravelSync trips." : searched ? "Try widening the maximum distance or changing the interest mix." : "Submit the form above to see ranked destination suggestions."}</p></div>{results.length > 0 && <span className="result-count">{results.length} matches</span>}</div>
          {results.length > 0 && <div className="result-grid">{results.map((result, index) => <article className="result-card" key={`${result.Destination}-${result.State}`}><div className="result-card__top"><span className="rank">0{index + 1}</span><span className="match-badge">{Math.round(result.final_score * 100)}% match</span></div><h3>{result.Destination}</h3><p className="result-location">{result.State} · {result.Region}</p><div className="result-stats"><div><span>Estimated budget</span><strong>₹{Number(result.estimated_trip_budget_inr).toLocaleString("en-IN")}</strong></div><div><span>Ideal stay</span><strong>{result.Ideal_Days} days</strong></div><div><span>From you</span><strong>{result.distance_km} km</strong></div></div><div className="result-checks"><span className={result.duration_score >= .8 ? "ok" : "soft"}><Check size={14}/> Duration</span><span className={result.budget_score >= .85 ? "ok" : "soft"}><Check size={14}/> Budget</span><span className={result.distance_score >= .75 ? "ok" : "soft"}><Check size={14}/> Distance</span></div><button type="button" className="choose-button" disabled={savingDestination === result.Destination} onClick={() => chooseDestination(result)}>{savingDestination === result.Destination ? "Saving…" : "Choose this destination"}<ArrowRight size={16}/></button></article>)}</div>}
          {!results.length && searched && !loading && <div className="empty-results"><Compass size={25}/><h3>No destination matched those constraints.</h3><p>The recommendation engine did not find an eligible candidate inside the practical limits you selected.</p></div>}
          {rules && <p className="results-footnote">{rules.duration}. {rules.budget}. {rules.distance}.</p>}
        </section>
      </main>
      <Footer />
    </div>
  );
}
