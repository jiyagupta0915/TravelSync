import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, CalendarDays, HeartPulse, Info, MapPin, Search, ShieldCheck } from "lucide-react";
import Sidebar from "../../components/Sidebar/Sidebar";
import { searchDestinations } from "../../services/recommendationApi";
import { getTravelHealth } from "../../services/healthApi";
import "./Health.css";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const FULL_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

function Bar({ label, value, max, note, muted }) {
  return (
    <div className="hs-bar">
      <span className="hs-bar__label">{label}</span>
      <div className="hs-bar__track">
        <div className={`hs-bar__fill${muted ? " hs-bar__fill--muted" : ""}`} style={{ width: `${max ? (value / max) * 100 : 0}%` }} />
      </div>
      <span className="hs-bar__value">{note ?? value}</span>
    </div>
  );
}


function SourceLinks({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <p className="hs-sources">
      Learn more:{" "}
      {sources.map((src, i) => (
        <span key={src.url}>
          <a href={src.url} target="_blank" rel="noreferrer">{src.name}</a>
          {i < sources.length - 1 ? " · " : ""}
        </span>
      ))}
    </p>
  );
}

function CurrentSituation({ alerts }) {
  const hasAlert = alerts.status === "alert";
  return (
    <section className="hs-card">
      <h3 className="hs-h3">Current situation</h3>
      <div className={`hs-status ${hasAlert ? "hs-status--alert" : "hs-status--none"}`}>
        {hasAlert ? <AlertTriangle size={18} /> : <ShieldCheck size={18} />}
        <strong>{alerts.message}</strong>
      </div>

      {alerts.active.map((a) => (
        <div key={a.id} className={`hs-alert hs-alert--${a.severity}`}>
          <div className="hs-alert__head">
            <strong>{a.title}</strong>
            <span>{a.reported_date}</span>
          </div>
          <p>{a.summary}</p>
          <a href={a.source_url} target="_blank" rel="noreferrer">Source: {a.source_name}</a>
        </div>
      ))}

      {alerts.earlier.length > 0 && (
        <>
          <h4 className="hs-h4">Earlier alerts (no longer marked active)</h4>
          {alerts.earlier.map((a) => (
            <div key={a.id} className="hs-alert hs-alert--earlier">
              <div className="hs-alert__head">
                <strong>{a.title}</strong>
                <span>{a.reported_date}</span>
              </div>
              <p>{a.summary}</p>
              <a href={a.source_url} target="_blank" rel="noreferrer">Source: {a.source_name}</a>
            </div>
          ))}
        </>
      )}

      <div className="hs-note">
        <Info size={16} />
        <span>{alerts.notes.join(" ")}</span>
      </div>
    </section>
  );
}

export default function HealthSafety() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [month, setMonth] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!query.trim() || selected) { setResults([]); return; }
      try { const res = await searchDestinations(query); setResults(res.results || []); }
      catch { setResults([]); }
    }, 220);
    return () => clearTimeout(timer);
  }, [query, selected]);

  async function load(destination, m) {
    setLoading(true); setError("");
    try { setData(await getTravelHealth(destination, m)); }
    catch (err) { setData(null); setError(err.message); }
    finally { setLoading(false); }
  }

  function choose(item) {
    setSelected(item); setQuery(item.Destination); setResults([]);
    load(item.Destination, month);
  }

  function changeMonth(value) {
    setMonth(value);
    if (selected) load(selected.Destination, value);
  }

  const yearlyMax = data?.yearly ? Math.max(...data.yearly.map((y) => y.outbreaks)) : 0;
  // Opened from a saved trip: /health?destination=Manali loads that destination straight away.
  useEffect(() => {
    const name = searchParams.get("destination");
    if (!name) return undefined;
    let active = true;
    searchDestinations(name)
      .then((res) => {
        const match = (res.results || []).find((r) => r.Destination.toLowerCase() === name.toLowerCase());
        if (active && match) choose(match);
      })
      .catch(() => {});
    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const mixMax = data?.disease_mix ? Math.max(...data.disease_mix.map((d) => d.outbreaks)) : 0;

  return (
    <div className="dashboard">
      <Sidebar />
      <div className="dashboard__main">
        <main className="dashboard__content">
          <div className="dashboard__welcome">
            <div>
              <span className="dashboard__eyebrow">TRAVEL HEALTH &amp; SAFETY</span>
              <h1 className="dashboard__greeting">What has happened here before? 🩺</h1>
              <p className="dashboard__subgreeting">
                A historical look at reported disease outbreaks in your destination&apos;s state, with unusual periods and seasonal patterns found by machine learning. This is not a prediction.
              </p>
            </div>
          </div>

          <section className="hs-card hs-search">
            <div className="hs-search__row">
              <div className="hs-search__input">
                <Search size={18} />
                <input
                  value={query}
                  onChange={(e) => { setQuery(e.target.value); setSelected(null); setData(null); }}
                  placeholder="Search for a destination"
                />
              </div>
              <label className="hs-search__month">
                <CalendarDays size={16} />
                <select value={month} onChange={(e) => changeMonth(e.target.value)}>
                  <option value="">Any month</option>
                  {FULL_MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
                </select>
              </label>
            </div>
            {results.length > 0 && (
              <div className="hs-suggest">
                {results.map((item) => (
                  <button type="button" key={`${item.Destination}-${item.State}`} onClick={() => choose(item)}>
                    <MapPin size={15} /> <strong>{item.Destination}</strong> <small>{item.State}</small>
                  </button>
                ))}
              </div>
            )}
          </section>

          {loading && <div className="dashboard__empty">Loading health information…</div>}
          {error && <div className="dashboard__empty dashboard__empty--error">{error}</div>}
          {!loading && !error && !data && (
            <div className="dashboard__empty">
              <HeartPulse size={25} />
              <h3>Choose a destination</h3>
              <p>Pick a place above to see its state&apos;s historical outbreak activity.</p>
            </div>
          )}

          {data && !loading && (
            <div className="hs-stack">
              {data.is_synthetic && (
                <div className="hs-banner">
                  <AlertTriangle size={18} />
                  <span><strong>Demo data.</strong> The outbreak records on this page are synthetic and do not describe real events.</span>
                </div>
              )}

              <section className="hs-card">
                <h2 className="hs-title">{data.destination}, {data.state}</h2>
                {data.has_data ? (
                  <p className="hs-muted">
                    {data.total_outbreaks.toLocaleString()} reported outbreaks · {data.years_covered[0]}–{data.years_covered[1]} · data through {data.data_through}
                  </p>
                ) : (
                  <p className="hs-muted">{data.message}</p>
                )}
              </section>

              <CurrentSituation alerts={data.current_alerts} />

              {data.has_data && (
                <>
                  {data.travel_month && (
                    <section className="hs-card">
                      <h3 className="hs-h3">Travelling in {data.travel_month}</h3>
                      {data.elevated_for_month.length === 0 ? (
                        <p className="hs-muted">No disease group stands out in {data.travel_month} compared with a typical month.</p>
                      ) : (
                        data.elevated_for_month.map((e) => (
                          <div key={e.group} className="hs-elevated">
                            <strong>{e.label}</strong> outbreaks were reported about {e.ratio}× more than a typical month.
                            <ul>{e.precautions.map((t) => <li key={t}>{t}</li>)}</ul>
                            <SourceLinks sources={e.sources} />
                          </div>
                        ))
                      )}
                    </section>
                  )}

                  <div className="hs-grid">
                    <section className="hs-card">
                      <h3 className="hs-h3">Outbreak reports per year</h3>
                      {data.yearly.map((y) => (
                        <Bar key={y.year} label={y.year} value={y.outbreaks} max={yearlyMax} muted={y.partial}
                             note={y.partial ? `${y.outbreaks} (partial)` : y.outbreaks} />
                      ))}
                      <p className="hs-muted hs-small">Most reports in a full year: {data.peak_year}.</p>
                    </section>

                    <section className="hs-card">
                      <h3 className="hs-h3">What kinds of outbreaks</h3>
                      {data.disease_mix.map((d) => (
                        <Bar key={d.group} label={d.label} value={d.outbreaks} max={mixMax} note={`${Math.round(d.share * 100)}%`} />
                      ))}
                      <p className="hs-muted hs-small">
                        Most reported: {data.top_diseases.slice(0, 3).map((d) => d.disease).join(", ")}.
                      </p>
                    </section>
                  </div>

                  <section className="hs-card">
                    <h3 className="hs-h3">Seasonal pattern</h3>
                    <div className="hs-season">
                      <div className="hs-season__head">
                        <span />
                        {MONTHS.map((m) => <span key={m}>{m[0]}</span>)}
                      </div>
                      {data.seasonal.map((s) => {
                        const top = Math.max(...s.monthly_share);
                        return (
                          <div key={s.group} className="hs-season__row">
                            <span className="hs-season__label">{s.label}</span>
                            {s.monthly_share.map((v, i) => (
                              <span key={i} className="hs-season__cell" title={`${FULL_MONTHS[i]}: ${Math.round(v * 100)}% of reports`}
                                    style={{ opacity: 0.12 + 0.88 * (v / top) }} />
                            ))}
                            <span className="hs-season__peaks">Peak: {s.peak_months.map((m) => m.slice(0, 3)).join(", ")}</span>
                          </div>
                        );
                      })}
                    </div>
                  </section>

                  <section className="hs-card">
                    <h3 className="hs-h3">🔎 Machine learning insights</h3>
                    <h4 className="hs-h4">Unusually busy months (Isolation Forest)</h4>
                    {data.unusual_months.length === 0 ? (
                      <p className="hs-muted">No month stood out as unusual for this state.</p>
                    ) : (
                      <ul className="hs-list">
                        {data.unusual_months.map((m) => (
                          <li key={`${m.year}-${m.month}`}>
                            <strong>{m.month} {m.year}</strong>: {m.outbreaks} outbreaks reported, about {m.times_normal}× a typical {m.month}. Mostly {m.top_disease}.
                          </li>
                        ))}
                      </ul>
                    )}
                    <h4 className="hs-h4">Unusually large single outbreaks</h4>
                    {data.notable_outbreaks.length === 0 ? (
                      <p className="hs-muted">None flagged.</p>
                    ) : (
                      <ul className="hs-list">
                        {data.notable_outbreaks.map((o, i) => (
                          <li key={i}><strong>{o.disease}</strong> in {o.district}, {o.date}: {o.cases} cases, {o.deaths} deaths.</li>
                        ))}
                      </ul>
                    )}
                    {data.cluster && (
                      <>
                        <h4 className="hs-h4">States with a similar disease pattern (K-Means)</h4>
                        <p className="hs-muted">
                          {data.state} groups with <strong>{data.cluster.label}</strong> states
                          {data.cluster.similar_states.length > 0 && <>, such as {data.cluster.similar_states.slice(0, 5).join(", ")}</>}.
                        </p>
                      </>
                    )}
                  </section>

                  <section className="hs-card">
                    <h3 className="hs-h3">🛡️ Traveller precautions</h3>
                    <p className="hs-muted hs-small">General public-health advice, not medical advice. Check the linked pages for detail.</p>
                    {data.precautions.map((p) => (
                      <div key={p.group} className="hs-prec">
                        <strong>{p.label}</strong>
                        <ul>{p.tips.map((t) => <li key={t}>{t}</li>)}</ul>
                        <SourceLinks sources={p.sources} />
                      </div>
                    ))}
                  </section>
                </>
              )}

              <section className="hs-card hs-card--quiet">
                <h3 className="hs-h3">Good to know</h3>
                <ul className="hs-list">{data.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
                <p className="hs-muted hs-small">Official sources: {data.official_sources.join("; ")}.</p>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
