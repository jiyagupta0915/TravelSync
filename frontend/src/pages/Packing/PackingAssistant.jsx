import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Shirt, CloudRain, Plug, FileText, Backpack, HeartPulse,
  CloudSun, Sparkles, Plus, Trash2, ArrowLeft,
} from "lucide-react";
import Sidebar from "../../components/Sidebar/Sidebar";
import { getTrips } from "../../services/tripApi";
import {
  getPackingList, generatePackingList, updatePackingList, setTripDates,
} from "../../services/packingApi";
import "./Packing.css";

const CATEGORY_META = {
  Clothing: { icon: Shirt, accent: "var(--pastel-blue)" },
  Weather: { icon: CloudRain, accent: "var(--pastel-aqua)" },
  Electronics: { icon: Plug, accent: "var(--pastel-lavender)" },
  Documents: { icon: FileText, accent: "var(--pastel-peach)" },
  Activity: { icon: Backpack, accent: "var(--pastel-pink)" },
  Health: { icon: HeartPulse, accent: "var(--pastel-pink)" },
};

function groupByCategory(items) {
  const groups = {};
  for (const item of items) {
    if (!groups[item.category]) groups[item.category] = [];
    groups[item.category].push(item);
  }
  return groups;
}

export default function PackingAssistant() {
  const { tripId } = useParams();
  const navigate = useNavigate();

  const [trip, setTrip] = useState(null);
  const [packingList, setPackingList] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savingDates, setSavingDates] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [newItemName, setNewItemName] = useState("");

  async function loadEverything() {
    setLoading(true);
    setError("");
    try {
      const tripsData = await getTrips();
      const currentTrip = (tripsData.trips || []).find((t) => t.id === tripId);
      setTrip(currentTrip || null);

      try {
        const { packing_list } = await getPackingList(tripId);
        setPackingList(packing_list);
      } catch {
        const { packing_list } = await generatePackingList(tripId);
        setPackingList(packing_list);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEverything();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId]);

  async function handleToggle(itemId) {
    const updatedItems = packingList.items.map((item) =>
      item.id === itemId ? { ...item, packed: !item.packed } : item
    );
    setPackingList({ ...packingList, items: updatedItems });
    try {
      await updatePackingList(tripId, updatedItems);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAddItem(category) {
    if (!newItemName.trim()) return;
    const customItem = {
      id: `c${Date.now()}`,
      category,
      name: newItemName.trim(),
      quantity: 1,
      packed: false,
      source: "custom",
    };
    const updatedItems = [...packingList.items, customItem];
    setPackingList({ ...packingList, items: updatedItems });
    setNewItemName("");
    try {
      await updatePackingList(tripId, updatedItems);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteItem(itemId) {
    const updatedItems = packingList.items.filter((item) => item.id !== itemId);
    setPackingList({ ...packingList, items: updatedItems });
    try {
      await updatePackingList(tripId, updatedItems);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSaveDates(event) {
    event.preventDefault();
    if (!startDate || !endDate) return;
    setSavingDates(true);
    setError("");
    try {
      await setTripDates(tripId, startDate, endDate);
      const { packing_list } = await generatePackingList(tripId, { regenerate: true });
      setPackingList(packing_list);
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingDates(false);
    }
  }

  if (loading) {
    return (
      <div className="dashboard">
        <Sidebar />
        <div className="dashboard__main">
          <main className="dashboard__content"><div className="dashboard__empty">Loading packing list…</div></main>
        </div>
      </div>
    );
  }

  const groups = packingList ? groupByCategory(packingList.items) : {};
  const totalItems = packingList?.items.length || 0;
  const packedItems = packingList?.items.filter((i) => i.packed).length || 0;
  const progressPct = totalItems ? Math.round((packedItems / totalItems) * 100) : 0;

  return (
    <div className="dashboard">
      <Sidebar />
      <div className="dashboard__main">
        <main className="dashboard__content">
          <button className="packing-back" onClick={() => navigate("/packing")}>
            <ArrowLeft size={16} /> All trips
          </button>

          <div className="dashboard__welcome">
            <div>
              <span className="dashboard__eyebrow">SMART PACKING ASSISTANT</span>
              <h1 className="dashboard__greeting">
                Packing for {trip?.destination || "your trip"} 🎒
              </h1>
            </div>
          </div>

          {error && <div className="dashboard__empty dashboard__empty--error">{error}</div>}

          {packingList && (
            <>
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
                    <p>Add them to refine this list with a real weather forecast.</p>
                  </div>
                  <div className="packing-dates-card__inputs">
                    <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
                    <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
                    <button type="submit" className="btn btn--primary" disabled={savingDates}>
                      {savingDates ? "Refining…" : "Refine with forecast"}
                    </button>
                  </div>
                </form>
              )}

              <div className="packing-progress">
                <span>{packedItems} of {totalItems} packed</span>
                <div className="packing-progress__bar">
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
                              <button className="packing-item__delete" onClick={() => handleDeleteItem(item.id)} aria-label="Remove item">
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
                          value={newItemName}
                          onChange={(e) => setNewItemName(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && handleAddItem(category)}
                        />
                        <button onClick={() => handleAddItem(category)} aria-label="Add item"><Plus size={16} /></button>
                      </div>
                    </section>
                  );
                })}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}