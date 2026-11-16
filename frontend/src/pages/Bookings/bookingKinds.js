import { Bed, Bus, Plane, Sparkles, Ticket, Train } from "lucide-react";

export const KINDS = [
  { id: "hotel", label: "Hotel / stay", icon: Bed },
  { id: "flight", label: "Flight", icon: Plane },
  { id: "train", label: "Train", icon: Train },
  { id: "bus", label: "Bus", icon: Bus },
  { id: "activity", label: "Activity / ticket", icon: Sparkles },
  { id: "other", label: "Other", icon: Ticket },
];
export const KIND = Object.fromEntries(KINDS.map((k) => [k.id, k]));
export const kindOf = (id) => KIND[id] || KIND.other;

export const EMPTY_BOOKING = { scope: "trip", trip_id: "", group_id: "", share_to_chat: false, kind: "hotel", title: "", provider: "", reference: "", start_date: "", end_date: "", amount: "", notes: "" };

export const formatDate = (iso) => (iso ? new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${iso}T00:00:00`)) : "");
export const formatRange = (start, end) => (start ? `${formatDate(start)}${end && end !== start ? ` → ${formatDate(end)}` : ""}` : end ? formatDate(end) : "");
