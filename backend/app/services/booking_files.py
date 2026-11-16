"""
Files attached to bookings (tickets, e-tickets, hotel vouchers, ID copies).

WHERE THEY LIVE. Each file is one document in the `booking_files` collection of the same MongoDB the rest of the app
uses (the bytes are in `data`). That is deliberate:
  * Files are capped at 5 MB, far below MongoDB's 16 MB document limit, so GridFS is not needed.
  * No second service to run, pay for or secure, and the tests run on the same in-memory fake database.
  * Files are private: there is NO public URL. The only way to read one is GET /api/bookings/{id}/files/{file_id},
    which checks the logged-in user may see that booking (its owner, or a member of its group).
The booking document itself stores no file data; its attachment list is built from `booking_files` (metadata only).

WHAT IS ACCEPTED. PDF, PNG, JPEG and WebP only, decided from the file's first bytes, never from the file name or the
Content-Type the browser claims. At most 5 MB each and 5 files per booking.
Moving to S3 / Cloudinary later only means replacing `data` with a storage key; the router would not change.
"""

import re

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES_PER_BOOKING = 5

# (content type, extension) by file signature.
_SIGNATURES = (
    (b"%PDF-", "application/pdf", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
)


def detect_type(data: bytes) -> tuple[str, str] | None:
    """(content_type, extension) for an allowed file, or None."""
    for magic, content_type, ext in _SIGNATURES:
        if data.startswith(magic):
            return content_type, ext
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


def safe_filename(raw: str | None, ext: str) -> str:
    """A display name that cannot carry a path or control characters, always ending in the real extension."""
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f\"<>|:*?]", "", name).strip(" .")
    stem = name.rsplit(".", 1)[0] if "." in name else name
    stem = stem.strip(" .")[:80] or "ticket"
    return f"{stem}.{ext}"


async def delete_bookings_cascade(db, query: dict) -> None:
    """Deletes the bookings matching `query` and every file attached to them."""
    ids = [d["_id"] async for d in db.bookings.find(query, {"_id": 1})]
    if ids:
        await db.booking_files.delete_many({"booking_id": {"$in": ids}})
        await db.bookings.delete_many({"_id": {"$in": ids}})
