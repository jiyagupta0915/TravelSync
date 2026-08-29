import { useNavigate } from "react-router-dom";
import {
  Compass,
  MapPin,
  CloudSun,
  Package,
  ShieldCheck,
  Users,
  Vote,
  Ticket,
  History,
  Sparkles,
} from "lucide-react";
import Navbar from "../../components/Navbar/Navbar";
import FeatureCard from "../../components/FeatureCard/FeatureCard";
import Footer from "../../components/Footer/Footer";
import "./Landing.css";

const features = [
  { icon: Compass, title: "Smart Trip Planner", description: "Personalized destination discovery based on travel preferences.", accent: "var(--pastel-blue)" },
  { icon: MapPin, title: "Explore Places & Hotels", description: "Discover attractions, places and recommended stays.", accent: "var(--pastel-aqua)" },
  { icon: CloudSun, title: "Weather Updates", description: "Destination-specific weather information for better planning.", accent: "var(--pastel-peach)" },
  { icon: Package, title: "Smart Packing Assistant", description: "Personalized packing suggestions based on destination, weather and duration.", accent: "var(--pastel-peach)" },
  { icon: ShieldCheck, title: "Travel Health & Safety", description: "Destination-specific health information, alerts and historical insights.", accent: "var(--pastel-aqua)" },
  { icon: Users, title: "Collaborative Travel Hub", description: "Create groups, communicate and plan together.", accent: "var(--pastel-pink)" },
  { icon: Vote, title: "Destination Voting", description: "Share destination options and decide together as a group.", accent: "var(--pastel-pink)" },
  { icon: Ticket, title: "Bookings & Tickets", description: "Keep travel-related booking information organized.", accent: "var(--pastel-blue)" },
  { icon: History, title: "Travel History", description: "Access previous trips and travel information.", accent: "var(--pastel-lavender)" },
  { icon: Sparkles, title: "AI Travel Assistant", description: "Conversational assistance for travel-related questions.", accent: "var(--pastel-lavender)" },
];

const preferenceChips = [
  { label: "Mood", value: "Relaxed" },
  { label: "Duration", value: "3–5 days" },
  { label: "Budget", value: "₹5k–₹20k" },
  { label: "Travellers", value: "2 Friends" },
  { label: "Vibe", value: "Beach" },
  { label: "Distance", value: "Within 1000 km" },
];

const valueStrip = [
  "Personalized Recommendations",
  "Collaborative Planning",
  "All-in-One Travel Hub",
  "AI Assistance",
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <>
      <Navbar />

      <main>
        {/* ================= HERO ================= */}
        <section id="top" className="hero">
          <div className="hero__content">
            <h1 className="hero__headline">
              Plan Smarter,
              <br />
              Travel <span className="hero__highlight">Together.</span>
            </h1>
            <p className="hero__subtext">
              Discover amazing destinations, plan with ease, stay prepared, and create
              unforgettable memories with TravelSync.
            </p>
            <div className="hero__actions">
              <button className="btn btn--primary" onClick={() => navigate("/signup")}>
                Plan Your Trip
              </button>
              <a href="#features" className="btn btn--ghost">
                See How It Works
              </a>
            </div>
          </div>

          <div className="hero__visual" aria-hidden="true">
            {/* Signature illustration: a minimal flight route connecting
                two waypoints, layered over soft pastel blobs. */}
            <svg viewBox="0 0 480 520" className="hero__svg">
              <defs>
                <filter id="soften" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="46" />
                </filter>
              </defs>

              <circle cx="150" cy="140" r="150" fill="var(--pastel-blue)" filter="url(#soften)" opacity="0.85" />
              <circle cx="330" cy="390" r="130" fill="var(--pastel-lavender)" filter="url(#soften)" opacity="0.75" />

              <path
                d="M100 400 C 160 300, 250 320, 280 220 S 360 90, 390 55"
                stroke="var(--ink)"
                strokeWidth="2.5"
                strokeDasharray="7 11"
                strokeLinecap="round"
                fill="none"
              />

              <circle cx="100" cy="400" r="7" fill="var(--ink)" />
              <circle cx="280" cy="220" r="7" fill="var(--ink)" />

              <g transform="translate(390, 55)">
                <path
                  d="M0 -24 C13 -24 22 -14 22 -2 C22 14 0 30 0 30 C0 30 -22 14 -22 -2 C-22 -14 -13 -24 0 -24 Z"
                  fill="var(--pastel-pink)"
                  stroke="var(--ink)"
                  strokeWidth="2"
                />
                <circle cx="0" cy="-4" r="6" fill="var(--ink)" />
              </g>
            </svg>

            <div className="hero__floating-card">
              <span className="hero__floating-dot" />
              Next stop: Goa
            </div>
          </div>
        </section>

        {/* ================= RECOMMENDATION PREVIEW ================= */}
        <section id="recommend-preview" className="preview">
          <div className="preview__text">
            <h2>Not sure where to go?</h2>
            <p>Tell us your preferences and we'll recommend destinations for you.</p>
          </div>

          <div className="preview__chips">
            {preferenceChips.map((chip) => (
              <div key={chip.label} className="preview-chip">
                <span className="preview-chip__label">{chip.label}</span>
                <span className="preview-chip__value">{chip.value}</span>
              </div>
            ))}
          </div>

          <button className="btn btn--primary" onClick={() => navigate("/signup")}>
            Find My Destination ✨
          </button>
        </section>

        {/* ================= FEATURES ================= */}
        <section id="features" className="features">
          <h2 className="features__heading">Everything your trip needs, in one place</h2>
          <div className="features__grid">
            {features.map((feature) => (
              <FeatureCard
                key={feature.title}
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
                accentColor={feature.accent}
              />
            ))}
          </div>
        </section>

        {/* ================= VALUE STRIP ================= */}
        <section className="value-strip">
          {valueStrip.map((value) => (
            <span key={value} className="value-strip__item">
              {value}
            </span>
          ))}
        </section>

        {/* ================= ABOUT ================= */}
        <section id="about" className="about">
          <h2>Why we built TravelSync</h2>
          <p>
            TravelSync started as a university software engineering project with one
            goal — make trip planning feel less like busywork and more like part of the
            adventure. What you're seeing here is an early look at what our team is
            building together.
          </p>
        </section>
      </main>

      <Footer />
    </>
  );
}