"""
Keeps track of which browsers have a live chat socket open, per group, and pushes new messages to them.

The socket is receive-only: messages are still SENT with POST /api/groups/{id}/messages (so validation,
membership checks and tests stay in one place). After a message is saved, post_message calls
`hub.broadcast_message`, which pushes it to everyone connected to that group.

Connections live in this process's memory, so this works with one server process (fine for development
and a college project). Running several workers would need something shared like Redis.
"""

import logging

from fastapi import WebSocket

logger = logging.getLogger("travelsync.chat")


class ChatHub:
    def __init__(self) -> None:
        # group id (str) -> {websocket: user id (str)}
        self._rooms: dict[str, dict[WebSocket, str]] = {}

    def add(self, group_id: str, ws: WebSocket, user_id: str) -> None:
        self._rooms.setdefault(group_id, {})[ws] = user_id

    def remove(self, group_id: str, ws: WebSocket) -> None:
        room = self._rooms.get(group_id)
        if room is None:
            return
        room.pop(ws, None)
        if not room:
            del self._rooms[group_id]

    async def broadcast_message(self, group_id: str, message: dict, sender_id: str) -> None:
        """Sends `message` to every open socket in the group. `is_me` is set per connection."""
        for ws, user_id in list(self._rooms.get(group_id, {}).items()):
            try:
                await ws.send_json({"type": "message", "message": {**message, "is_me": user_id == sender_id}})
            except Exception:  # a dead socket must never break sending a message
                logger.info("Dropping a dead chat socket")
                self.remove(group_id, ws)
    async def broadcast_deleted(self, group_id: str, message_id: str) -> None:
    #Tells everyone in the group that a message was (soft) deleted, so it disappears live.
        for ws in list(self._rooms.get(group_id, {})):
            try:
                await ws.send_json({"type": "message_deleted", "id": message_id})
            except Exception:
                self.remove(group_id, ws)

    async def broadcast_event(self, group_id: str, event: dict, exclude_user: str | None = None) -> None:
        """Sends the same small event (e.g. {"type": "suggestions_changed"}) to everyone in the group, optionally
        skipping one user's own connections."""
        for ws, user_id in list(self._rooms.get(group_id, {}).items()):
            if user_id == exclude_user:
                continue
            try:
                await ws.send_json(event)
            except Exception:
                self.remove(group_id, ws)

    async def close_user(self, group_id: str, user_id: str) -> None:
        """Disconnects one user from a group (used when they leave it)."""
        for ws, uid in list(self._rooms.get(group_id, {}).items()):
            if uid == user_id:
                await self._close(group_id, ws)

    async def close_group(self, group_id: str) -> None:
        """Disconnects everyone from a group (used when it is deleted)."""
        for ws in list(self._rooms.get(group_id, {})):
            await self._close(group_id, ws)

    async def _close(self, group_id: str, ws: WebSocket) -> None:
        self.remove(group_id, ws)
        try:
            await ws.close(code=1008)
        except Exception:
            pass


hub = ChatHub()