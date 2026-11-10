import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { MessageCircle, Send, X } from "lucide-react";
import { askAssistant } from "../../services/chatApi";
import "./ChatWidget.css";

const WELCOME = {
  role: "bot",
  text: "Hi! I'm the TravelSync assistant. I answer from TravelSync's own data: destinations, top places, packing, health alerts, and your trips and groups.",
  items: [], links: [],
  suggestions: ["Top places in Goa", "What should I pack for Manali?", "Any health alerts in Kerala?", "Suggest a beach destination", "Show my trips"],
};

// The floating assistant, shown on every page inside the app shell. It is mounted once by AppShell, so the
// conversation survives moving between pages and is discarded on logout. Answers come from POST /api/chat, which
// is built on TravelSync's own data; if the server used its optional AI model instead, the answer is labelled.
export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const destination = useRef(null);          // what the conversation is about, sent back with the next question
  const logRef = useRef(null);
  const inputRef = useRef(null);
  const launcherRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    inputRef.current?.focus();
    const onKeyDown = (event) => { if (event.key === "Escape") { setOpen(false); launcherRef.current?.focus(); } };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  useEffect(() => {
    if (open && logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [open, messages.length, busy]);

  async function send(question) {
    const body = question.trim();
    if (!body || busy) return;
    setMessages((previous) => [...previous, { role: "user", text: body }]);
    setText("");
    setBusy(true);
    try {
      const data = await askAssistant(body, destination.current);
      destination.current = data.destination || null;
      setMessages((previous) => [...previous, { role: "bot", items: [], links: [], suggestions: [], ...data.reply, ai: data.source === "ai-model" }]);
    } catch (err) {
      setMessages((previous) => [...previous, { role: "bot", error: true, text: err.message || "I couldn't answer that right now. Please try again.", items: [], links: [], suggestions: [] }]);
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  const lastIndex = messages.length - 1;

  return (
    <div className="chat-widget">
      {open && (
        <section className="chat-widget__panel" role="dialog" aria-label="TravelSync assistant">
          <header className="chat-widget__header">
            <div><strong>TravelSync assistant</strong><small>Answers from TravelSync's own data</small></div>
            <button type="button" onClick={() => { setOpen(false); launcherRef.current?.focus(); }} aria-label="Close assistant"><X size={18} /></button>
          </header>

          <ul className="chat-widget__log" ref={logRef} role="log" aria-live="polite" aria-label="Conversation">
            {messages.map((m, index) => (
              <li key={index} className={`chat-widget__msg chat-widget__msg--${m.role}${m.error ? " is-error" : ""}`}>
                <p>{m.text}</p>
                {m.ai && <small className="chat-widget__ai-note">AI-generated answer. It may be wrong, so check important details.</small>}
                {m.items?.length > 0 && <ul>{m.items.map((item) => <li key={item}>{item}</li>)}</ul>}
                {m.links?.length > 0 && (
                  <div className="chat-widget__links">
                    {m.links.map((link) => <Link key={link.to} to={link.to} onClick={() => setOpen(false)}>{link.label}</Link>)}
                  </div>
                )}
                {/* Follow-up questions are only offered on the newest reply, so old ones don't pile up. */}
                {index === lastIndex && m.suggestions?.length > 0 && (
                  <div className="chat-widget__suggestions">
                    {m.suggestions.map((s) => <button type="button" key={s} onClick={() => send(s)} disabled={busy}>{s}</button>)}
                  </div>
                )}
              </li>
            ))}
            {busy && <li className="chat-widget__msg chat-widget__msg--bot chat-widget__typing" role="status">Looking that up…</li>}
          </ul>

          <form className="chat-widget__form" onSubmit={(event) => { event.preventDefault(); send(text); }}>
            <input ref={inputRef} value={text} onChange={(event) => setText(event.target.value)} maxLength={300}
              placeholder="Ask about a destination…" aria-label="Your question" />
            <button type="submit" disabled={busy || !text.trim()} aria-label="Send question"><Send size={16} /></button>
          </form>
        </section>
      )}

      <button type="button" ref={launcherRef} className="chat-widget__launcher" onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Close assistant" : "Open TravelSync assistant"} aria-expanded={open}>
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>
    </div>
  );
}
