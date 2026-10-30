import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Shirt, CloudRain, Plug, FileText, Backpack, HeartPulse,
  CloudSun, Sparkles, Plus, Trash2, ArrowLeft,
} from "lucide-react";
import { getTrip } from "../../services/tripApi";
import {
  getPackingList, generatePackingList, updatePackingList, setTripDates,
} from "../../services/packingApi";
import { isAbort } from "../../services/apiClient";
import "./Packing.css";

const CATEGORY_META = {
  Clothing: { icon: Shirt, accent: "var(--pastel-blue)" },
  Weather: { icon: CloudRain, accent: "var(--pastel-aqua)" },
  Electronics: { icon: Plug, accent: "var(--pastel-lavender)" },
  Documents: { icon: FileText, accent: "var(--pastel-peach)" },
  Activity: { icon: Backpack, accent: "var(--pastel-pink)" },
  Health: { icon: HeartPulse, accent: "var(--pastel-pink)" },
};

const MAX_ITEM_NAME = 80;
const MAX_ITEMS = 200;

function groupByCategory(items) {
  const groups = {};
  for (const item of items) {
    if (!groups[item.category]) groups[item.category] = [];
    groups[item.category].push(item);
  }
  return groups;
}

function newCustomItemId() {
  return `c${crypto.randomUUID().replace(/-/g, "").slice(0, 16)}`;
}

export default function PackingAssistant() {
  const { tripId } = useParams();
  const navigate = useNavigate();

  // `data` belongs to one trip; when the route changes to another trip it is stale and we show "loading".
  const [data, setData] = useState({ tripId: null, status: "loading", trip: null, list: null, error: "" });
  const [reloadKey, setReloadKey] = useState(0);
  const [actionError, setActionError] = useState("");
  const [savingDates, setSavingDates] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [drafts, setDrafts] = useState({});

  // Saves are sent one at a time, in order. `confirmedItems` is the last list the server accepted, so a failed
  // save can put the screen back to the truth instead of leaving a change that was never stored.
  const saveChain = useRef(Promise.resolve());
  const confirmedItems = useRef([]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    async function load() {
      try {
        const { trip } = await getTrip(tripId);
        let list;
        try {
          ({ packing_list: list } = await getPackingList(tripId));
        } catch (err) {
          // Only "there is no list yet" means generate one. Network/auth/server problems must NOT silently create data.
          if (err.status !== 404) throw err;
          ({ packing_list: list } = await generatePackingList(tripId));
        }
        if (!active) return;
        confirmedItems.current = list.items;
        setData({ tripId, status: "ready", trip, list, error: "" });
      } catch (err) {
        if (!active || isAbort(err)) return;
        setData({ tripId, status: err.kind === "notfound" ? "missing" : "error", trip: null, list: null, error: err.message });
      }
    }
    load();
    return () => { active = false; controller.abort(); };
  }, [tripId, reloadKey]);

  const current = data.tripId === tripId ? data : { status: "loading" };
  const { trip, list: packingList } = current;

  const setList = useCallback((updater) => {
    setData((previous) => (previous.list ? { ...previous, list: updater(previous.list) } : previous));
  }, []);

  // Optimistic update + ordered save + rollback on failure.
  const persistItems = useCallback((nextItems) => {
    setActionError("");
    setList((list) => ({ ...list, items: nextItems }));
    saveChain.current = saveChain.current.then(async () => {
      try {
        await updatePackingList(tripId, nextItems);
        confirmedItems.current = nextItems;
      } catch (err) {
        setList((list) => ({ ...list, items: confirmedItems.current }));
        setActionError(`${err.message} Your last change was not saved and has been undone.`);
      }
    });
  }, [tripId, setList]);

  function handleToggle(itemId) {
    persistItems(packingList.items.map((item) => (item.id === itemId ? { ...item, packed: !item.packed } : item)));
  }

  function handleDeleteItem(itemId) {
    persistItems(packingList.items.filter((item) => item.id !== itemId));
  }

  function handleAddItem(category) {
    const name = (drafts[category] || "").trim().replace(/\s+/g, " ");
    if (!name) return;
    if (name.length > MAX_ITEM_NAME) { setActionError(`Item names can be at most ${MAX_ITEM_NAME} characters.`); return; }
    if (packingList.items.length >= MAX_ITEMS) { setActionError(`A packing list can hold at most ${MAX_ITEMS} items.`); return; }
    if (packingList.items.some((item) => item.category === category && item.name.toLowerCase() === name.toLowerCase())) {
      setActionError(`"${name}" is already in ${category}.`);
      return;
    }
    setDrafts((previous) => ({ ...previous, [category]: "" }));
    persistItems([...packingList.items, { id: newCustomItemId(), category, name, quantity: 1, packed: false, source: "custom" }]);
  }

  async function handleSaveDates(event) {
    event.preventDefault();
    if (savingDates) return;
    if (!startDate || !endDate) { setActionError("Choose both a start and an end date."); return; }
    if (endDate < startDate) { setActionError("The end date can't be earlier than the start date."); return; }
    setSavingDates(true);
    setActionError("");
    try {
      await setTripDates(tripId, startDate, endDate);
      const { packing_list } = await generatePackingList(tripId, { regenerate: true });
      confirmedItems.current = packing_list.items;
      setList(() => packing_list);
      setData((previous) => ({ ...previous, trip: { ...previous.trip, start_date: startDate, end_date: endDate } }));
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSavingDates(false);
    }
  }

  const back = (
    <button className="packing-back" onClick={() => navigate("/packing")}>
      <ArrowLeft size={16} /> All trips
    </button>
  );

  if (current.status === "loading") {
    return <main className="dashboard__content"><div className="dashboard__empty" role="status">Loading packing list…</div></main>;
  }

  if (current.status === "missing") {
    return (
      <main className="dashboard__content">
        {back}
        <div className="dashboard__empty"><h3>Trip not found</h3><p>This trip doesn't exist or isn't yours.</p></div>
      </main>
    );
  }

  if (current.status === "error") {
    return (
      <main className="dashboard__content">
        {back}
        <div className="dashboard__empty dashboard__empty--error" role="alert">
          <h3>Couldn't load your packing list</h3>
          <p>{current.error}</p>
          <button className="btn btn--primary" onClick={() => { setData((p) => ({ ...p, tripId: null })); setReloadKey((k) => k + 1); }}>Try again</button>
        </div>
      </main>
    );
  }

  const groups = groupByCategory(packingList.items);
  const totalItems = packingList.items.length;
  const packedItems = packingList.items.filter((i) => i.packed).length;
  const progressPct = totalItems ? Math.round((packedItems / totalItems) * 100) : 0;

  return (
    <main className="dashboard__content">
      {back}

      <div className="dashboard__welcome">
        <div>
          <span className="dashboard__eyebrow">SMART PACKING ASSISTANT</span>
          <h1 className="dashboard__greeting">Packing for {trip?.destination || "your trip"} 🎒</h1>
        </div>
      </div>

      {actionError && <div className="dashboard__empty dashboard__empty--error" role="alert">{actionError}</div>}

      <div className={`packing-tier-badge packing-tier-badge--${packingList.tier}`}>
        {packingList.tier === "forecast" ? <CloudSun size={15} /> : <Sparkles size={15} />}
        {packingList.tier === "forecast"
          ? `Weather-checked — ${packingList.weather_summary}`
          : `Based on ${trip?.region || "destination"} climate & terrain profile`}
      </div>

      {packingList.tier === "climate" && (
        <form className="packing-dates-card" onSubmit={handleSaveDates}>
          <div>
            <strong>Know your exact travel dates?</strong>
            <p>Add them to refine this list with a real weather forecast. If the forecast can't be fetched, the climate-based list stays.</p>
          </div>
          <div className="packing-dates-card__inputs">
            <input type="date" aria-label="Trip start date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
            <input type="date" aria-label="Trip end date" value={endDate} min={startDate || undefined} onChange={(e) => setEndDate(e.target.value)} required />
            <button type="submit" className="btn btn--primary" disabled={savingDates}>
              {savingDates ? "Refining…" : "Refine with forecast"}
            </button>
          </div>
        </form>
      )}

      <div className="packing-progress">
        <span>{packedItems} of {totalItems} packed</span>
        <div className="packing-progress__bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progressPct} aria-label="Packing progress">
          <div className="packing-progress__fill" style={{ width: `${progressPct}%` }} />
        </div>
      </div>

      <div className="packing-categories">
        {Object.entries(groups).map(([category, items]) => {
          const meta = CATEGORY_META[category] || CATEGORY_META.Clothing;
          const Icon = meta.icon;
          return (
            <section className="packing-category-card" key={category}>
              <div className="packing-category-card__header">
                <div className="packing-category-card__icon" style={{ backgroundColor: meta.accent }}>
                  <Icon size={20} strokeWidth={1.75} />
                </div>
                <h3>{category}</h3>
              </div>

              <ul className="packing-item-list">
                {items.map((item) => (
                  <li key={item.id} className={item.packed ? "packing-item packing-item--packed" : "packing-item"}>
                    <label>
                      <input type="checkbox" checked={item.packed} onChange={() => handleToggle(item.id)} />
                      <span>{item.name}</span>
                    </label>
                    <div className="packing-item__right">
                      {item.quantity > 1 && <span className="packing-item__qty">×{item.quantity}</span>}
                      <button className="packing-item__delete" onClick={() => handleDeleteItem(item.id)} aria-label={`Remove ${item.name}`}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>

              <div className="packing-add-item">
                <input
                  type="text"
                  placeholder="Add an item…"
                  aria-label={`Add an item to ${category}`}
                  maxLength={MAX_ITEM_NAME}
                  value={drafts[category] || ""}
                  onChange={(e) => setDrafts((previous) => ({ ...previous, [category]: e.target.value }))}
                  onKeyDown={(e) => e.key === "Enter" && handleAddItem(category)}
                />
                <button onClick={() => handleAddItem(category)} aria-label={`Add item to ${category}`}><Plus size={16} /></button>
              </div>
            </section>
          );
        })}
      </div>
    </main>
  );
}
