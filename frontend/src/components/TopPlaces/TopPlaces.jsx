import { useEffect, useState } from "react";
import { CalendarDays, Clock, Compass, Star } from "lucide-react";
import { getTopPlaces } from "../../services/placesApi";
import "./TopPlaces.css";

// Each category gets one of the official pastel tones.
const CATEGORY_TONES = {
  Heritage: "peach",
  Nature: "aqua",
  Spiritual: "lavender",
  Adventure: "blue",
  Trekking: "blue",
  Beach: "blue",
  Culture: "pink",
  Food: "peach",
  Wildlife: "aqua",
  Relaxation: "pink",
  Sightseeing: "cream",
};

function formatDuration(hours) {
  const value = Number(hours);
  if (!value) return "";
  if (value < 1) return `${Math.round(value * 60)} min`;
  return `${value % 1 === 0 ? value : value.toFixed(1)} hr${value > 1 ? "s" : ""}`;
}

export default function TopPlaces({ destination, heading = true }) {
  const [places, setPlaces] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!destination) return undefined;
    let active = true;
    setLoading(true);
    setError("");
    setPlaces([]);
    getTopPlaces(destination)
      .then((data) => active && setPlaces(data.places || []))
      .catch((err) => active && setError(err.message || "Top places could not be loaded."))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [destination]);

  if (!destination) return null;

  return (
    <section className="top-places" aria-live="polite">
      {heading && (
        <div className="top-places__heading">
          <span className="section-kicker">TOP PLACES TO VISIT</span>
          <h3>Top {places.length || 5} places in {destination}</h3>
          <p>Ranked by traveller ratings and popularity.</p>
        </div>
      )}

      {loading && (
        <div className="top-places__list">
          {[1, 2, 3].map((item) => <div className="place-skeleton" key={item} />)}
        </div>
      )}

      {!loading && error && (
        <div className="top-places__empty"><Compass size={22} /><p>{error}</p></div>
      )}

      {!loading && !error && places.length > 0 && (
        <ol className="top-places__list">
          {places.map((place) => (
            <li className={`place-card ${place.rank === 1 ? "is-top" : ""}`} key={place.place_name}>
              <span className="place-card__rank">{String(place.rank).padStart(2, "0")}</span>
              <div className="place-card__body">
                <div className="place-card__title-row">
                  <h4>{place.place_name}</h4>
                  {place.rank === 1 && <span className="place-card__top-pick">Top pick</span>}
                </div>
                <p className="place-card__desc">{place.description}</p>
                <div className="place-card__meta">
                  <span className={`place-tag place-tag--${CATEGORY_TONES[place.category] || "cream"}`}>{place.category}</span>
                  <span><Star size={13} /> {Number(place.rating).toFixed(1)}</span>
                  <span><Clock size={13} /> {formatDuration(place.duration_hrs)}</span>
                  <span><CalendarDays size={13} /> {place.best_season}</span>
                </div>
                <div className="place-card__popularity" title={`Popularity ${Math.round(place.popularity * 100)}%`}>
                  <span>Popularity</span>
                  <div><i style={{ width: `${Math.round(place.popularity * 100)}%` }} /></div>
                  <b>{Math.round(place.popularity * 100)}%</b>
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
