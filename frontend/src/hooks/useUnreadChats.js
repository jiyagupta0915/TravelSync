import { useEffect, useState } from "react";
import { getUnreadChats } from "../services/groupApi";

const POLL_MS = 30_000;

// Fired on window by the chat after it has told the server "I've read this", so the badge updates straight away.
export const CHATS_READ_EVENT = "travelsync:chats-read";

// Total unread group-chat messages for the signed-in user. Checked on mount, every 30 seconds while the tab is
// visible, when the tab becomes visible again, and whenever a chat reports that it was read. Errors are ignored:
// the badge is a hint, and the next check will catch up.
export function useUnreadChats() {
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const check = () => {
      if (document.visibilityState !== "visible") return;
      getUnreadChats(controller.signal).then((data) => setTotal(data.total || 0)).catch(() => {});
    };
    check();
    const timer = setInterval(check, POLL_MS);
    window.addEventListener(CHATS_READ_EVENT, check);
    document.addEventListener("visibilitychange", check);
    return () => {
      controller.abort();
      clearInterval(timer);
      window.removeEventListener(CHATS_READ_EVENT, check);
      document.removeEventListener("visibilitychange", check);
    };
  }, []);

  return total;
}
