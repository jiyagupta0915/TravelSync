import { ACCEPTED_FILE_TYPES, MAX_FILES_PER_BOOKING, MAX_FILE_MB, uploadBookingFile } from "../services/bookingApi";

const ALLOWED_TYPES = ACCEPTED_FILE_TYPES.split(",");
export const fileSize = (bytes) => (bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`);

// Quick checks in the browser so people get an instant answer; the server checks the file's real contents again.
export function checkFiles(files, alreadyAttached = 0) {
  if (alreadyAttached + files.length > MAX_FILES_PER_BOOKING) return `A booking can have at most ${MAX_FILES_PER_BOOKING} files.`;
  for (const f of files) {
    if (!ALLOWED_TYPES.includes(f.type)) return `"${f.name}" isn't a PDF, PNG, JPEG or WebP file.`;
    if (f.size > MAX_FILE_MB * 1024 * 1024) return `"${f.name}" is larger than ${MAX_FILE_MB} MB.`;
    if (f.size === 0) return `"${f.name}" is empty.`;
  }
  return "";
}


// A server that doesn't have the upload route yet answers a bare "Not Found".
function uploadErrorText(err) {
  if (err.status === 404 && /^not found\.?$/i.test(err.message)) return "the server doesn't support file uploads yet (update the backend and restart it)";
  return err.message;
}

// Uploads one file after another and keeps going if one fails. Returns what was attached and what failed.
export async function uploadAll(bookingId, files) {
  const attachments = [];
  const failures = [];
  for (const file of files) {
    try { attachments.push((await uploadBookingFile(bookingId, file)).attachment); }
    catch (err) { failures.push(`${file.name}: ${uploadErrorText(err)}`); }
  }
  return { attachments, failures };
}

// Older servers may send bookings without these fields; never let that crash the page.
export const normalizeBooking = (b) => ({ ...b, attachments: Array.isArray(b.attachments) ? b.attachments : [], can_edit: b.can_edit ?? true });
