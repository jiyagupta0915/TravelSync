import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Bookings from "./Bookings";
import { checkFiles, normalizeBooking } from "../../utils/bookingFiles";
import { renderWithProviders } from "../../test/helpers";

vi.mock("../../services/tripApi", () => ({ getTrips: vi.fn(async () => ({ trips: [{ id: "t1", destination: "Goa", duration: 4 }] })) }));
vi.mock("../../services/groupApi", () => ({ listGroups: vi.fn(async () => ({ groups: [{ id: "g1", name: "Goa Gang" }] })) }));
vi.mock("../../services/bookingApi", () => ({
  ACCEPTED_FILE_TYPES: "application/pdf,image/png,image/jpeg,image/webp", MAX_FILE_MB: 5, MAX_FILES_PER_BOOKING: 5,
  bookingFileUrl: (id, fid, dl) => `/api/bookings/${id}/files/${fid}${dl ? "?download=1" : ""}`,
  listBookings: vi.fn(), createBooking: vi.fn(), updateBooking: vi.fn(), deleteBooking: vi.fn(async () => ({ deleted: true })),
  deleteBookingFile: vi.fn(async () => ({ deleted: true })), shareBookingToChat: vi.fn(async () => ({ shared: true })), uploadBookingFile: vi.fn(),
}));
import { createBooking, deleteBooking, deleteBookingFile, listBookings, shareBookingToChat, updateBooking, uploadBookingFile } from "../../services/bookingApi";

const file = (name, type, size = 100) => new File([new Uint8Array(size)], name, { type });
const PDF = { id: "f1", filename: "voucher.pdf", content_type: "application/pdf", size: 2048 };
const BOOKING = { id: "b1", scope: "personal", trip_id: "t1", group_id: null, group_name: null, kind: "hotel", title: "Taj Resort", provider: "Taj", reference: "PNR99", start_date: "2026-11-16", end_date: "2026-11-21", amount_inr: 5000, notes: "Sea view room", created_by: null, can_edit: true, attachments: [PDF] };
const GROUP_BOOKING = { ...BOOKING, id: "b2", scope: "group", trip_id: null, group_id: "g1", group_name: "Goa Gang", title: "Group hotel", created_by: "Bob", can_edit: false, attachments: [PDF] };

const renderPage = () => render(renderWithProviders(<Bookings />));
const dialog = () => screen.getByRole("dialog");

beforeEach(() => vi.clearAllMocks());

describe("file helpers", () => {
  it("accepts PDFs and images", () => expect(checkFiles([file("a.pdf", "application/pdf"), file("b.png", "image/png")])).toBe(""));
  it("rejects other types, empty and oversized files", () => {
    expect(checkFiles([file("a.exe", "application/x-msdownload")])).toMatch(/isn't a PDF/);
    expect(checkFiles([file("a.pdf", "application/pdf", 0)])).toMatch(/empty/);
    expect(checkFiles([file("a.pdf", "application/pdf", 6 * 1024 * 1024)])).toMatch(/larger than 5 MB/);
  });
  it("enforces the per-booking count including files already attached", () => {
    expect(checkFiles([file("a.pdf", "application/pdf")], 5)).toMatch(/at most 5/);
    expect(checkFiles([file("a.pdf", "application/pdf")], 4)).toBe("");
  });
  it("fills in fields an older server leaves out", () => {
    expect(normalizeBooking({ id: "x" })).toEqual({ id: "x", attachments: [], can_edit: true });
  });
});

describe("booking cards", () => {
  it("shows files on the card as links that open the file without opening the booking", async () => {
    listBookings.mockResolvedValue({ bookings: [BOOKING] });
    renderPage();
    const link = await screen.findByRole("link", { name: "Open voucher.pdf" });
    expect(link).toHaveAttribute("href", "/api/bookings/b1/files/f1");
    expect(link).toHaveAttribute("target", "_blank");
    await userEvent.click(link);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens every detail when the card is clicked", async () => {
    listBookings.mockResolvedValue({ bookings: [BOOKING] });
    renderPage();
    await userEvent.click((await screen.findByText("Taj Resort")).closest("li"));
    const d = within(dialog());
    expect(d.getByRole("heading", { name: "Taj Resort" })).toBeInTheDocument();
    ["Taj", "PNR99", "Sea view room", "₹5,000", "16 Nov 2026 → 21 Nov 2026"].forEach((t) => expect(d.getByText(t)).toBeInTheDocument());
    expect(d.getByRole("link", { name: "Open voucher.pdf" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("asks before deleting a booking, and Cancel keeps it", async () => {
    listBookings.mockResolvedValue({ bookings: [BOOKING] });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Delete Taj Resort" }));
    expect(within(dialog()).getByText("Delete this booking?")).toBeInTheDocument();
    expect(within(dialog()).getByRole("button", { name: "Cancel" })).toHaveFocus();
    await userEvent.click(within(dialog()).getByRole("button", { name: "Cancel" }));
    expect(deleteBooking).not.toHaveBeenCalled();
    expect(screen.getByText("Taj Resort")).toBeInTheDocument();
  });

  it("deletes the booking once confirmed", async () => {
    listBookings.mockResolvedValue({ bookings: [BOOKING] });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Delete Taj Resort" }));
    await userEvent.click(within(dialog()).getByRole("button", { name: "Delete booking" }));
    await waitFor(() => expect(deleteBooking).toHaveBeenCalledWith("b1"));
    await waitFor(() => expect(screen.queryByText("Taj Resort")).not.toBeInTheDocument());
  });

  it("keeps the booking and shows the reason when deleting fails", async () => {
    listBookings.mockResolvedValue({ bookings: [BOOKING] });
    deleteBooking.mockRejectedValueOnce(new Error("Server is down."));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Delete Taj Resort" }));
    await userEvent.click(within(dialog()).getByRole("button", { name: "Delete booking" }));
    expect(await within(dialog()).findByText("Server is down.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View details of Taj Resort" })).toBeInTheDocument();
  });

  it("hides Delete on bookings the user may not change", async () => {
    listBookings.mockResolvedValue({ bookings: [GROUP_BOOKING] });
    renderPage();
    await screen.findByText("Group hotel");
    expect(screen.getByText(/added by Bob/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Delete Group hotel/ })).not.toBeInTheDocument();
  });

  it("still renders when the server sends bookings without attachments or can_edit", async () => {
    const old = { ...BOOKING };
    delete old.attachments; delete old.can_edit;
    listBookings.mockResolvedValue({ bookings: [old] });
    renderPage();
    expect(await screen.findByText("Taj Resort")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete Taj Resort" })).toBeInTheDocument();
  });
});

describe("details dialog", () => {
  it("lets group members open files and post in chat, but not edit or delete", async () => {
    listBookings.mockResolvedValue({ bookings: [GROUP_BOOKING] });
    renderPage();
    await userEvent.click((await screen.findByText("Group hotel")).closest("li"));
    const d = within(dialog());
    expect(d.getByText(/Only Bob or the group owner can change/)).toBeInTheDocument();
    expect(d.queryByRole("button", { name: /Edit/ })).not.toBeInTheDocument();
    expect(d.queryByRole("button", { name: /Delete/ })).not.toBeInTheDocument();
    expect(d.queryByRole("button", { name: /Remove voucher/ })).not.toBeInTheDocument();
    expect(d.queryByRole("button", { name: /Attach/ })).not.toBeInTheDocument();
    await userEvent.click(d.getByRole("button", { name: /Post in chat/ }));
    expect(shareBookingToChat).toHaveBeenCalledWith("b2");
    expect(await screen.findByText(/posted in the Goa Gang chat/)).toBeInTheDocument();
  });

  it("edits a booking and comes back to its details", async () => {
    listBookings.mockResolvedValue({ bookings: [BOOKING] });
    updateBooking.mockResolvedValue({ booking: { ...BOOKING, title: "Taj Resort & Spa" } });
    renderPage();
    await userEvent.click((await screen.findByText("Taj Resort")).closest("li"));
    await userEvent.click(within(dialog()).getByRole("button", { name: /Edit/ }));
    const title = within(dialog()).getByLabelText("Title");
    expect(title).toHaveValue("Taj Resort");
    await userEvent.clear(title);
    await userEvent.type(title, "Taj Resort & Spa");
    await userEvent.click(within(dialog()).getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(updateBooking).toHaveBeenCalledWith("b1", expect.objectContaining({ title: "Taj Resort & Spa" })));
    expect(await within(dialog()).findByRole("heading", { name: "Taj Resort & Spa" })).toBeInTheDocument();
  });

  it("deletes from the details after confirming", async () => {
    listBookings.mockResolvedValue({ bookings: [BOOKING] });
    renderPage();
    await userEvent.click((await screen.findByText("Taj Resort")).closest("li"));
    await userEvent.click(within(dialog()).getByRole("button", { name: /Delete/ }));
    const dialogs = screen.getAllByRole("dialog");
    await userEvent.click(within(dialogs[dialogs.length - 1]).getByRole("button", { name: "Delete booking" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(deleteBooking).toHaveBeenCalledWith("b1");
  });

  it("asks before removing a file", async () => {
    listBookings.mockResolvedValue({ bookings: [BOOKING] });
    renderPage();
    await userEvent.click((await screen.findByText("Taj Resort")).closest("li"));
    await userEvent.click(within(dialog()).getByRole("button", { name: "Remove voucher.pdf" }));
    const dialogs = screen.getAllByRole("dialog");
    expect(within(dialogs[1]).getByText("Remove this file?")).toBeInTheDocument();
    await userEvent.click(within(dialogs[1]).getByRole("button", { name: "Remove file" }));
    await waitFor(() => expect(deleteBookingFile).toHaveBeenCalledWith("b1", "f1"));
    expect(await within(dialog()).findByText(/No tickets or documents attached yet/)).toBeInTheDocument();
  });

  it("attaches a file to an existing booking", async () => {
    listBookings.mockResolvedValue({ bookings: [{ ...BOOKING, attachments: [] }] });
    uploadBookingFile.mockResolvedValue({ attachment: { id: "f7", filename: "t.pdf", content_type: "application/pdf", size: 100 } });
    renderPage();
    await userEvent.click((await screen.findByText("Taj Resort")).closest("li"));
    await userEvent.upload(within(dialog()).getByLabelText("Attach files to Taj Resort"), file("t.pdf", "application/pdf"));
    expect(await within(dialog()).findByRole("link", { name: "Open t.pdf" })).toBeInTheDocument();
  });
});

describe("add booking", () => {
  it("creates a group booking, shares it to chat, and uploads the chosen files", async () => {
    listBookings.mockResolvedValue({ bookings: [] });
    createBooking.mockResolvedValue({ booking: { ...GROUP_BOOKING, can_edit: true, attachments: [] } });
    uploadBookingFile.mockResolvedValue({ attachment: { id: "f9", filename: "t.pdf", content_type: "application/pdf", size: 100 } });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Add booking/ }));
    await userEvent.click(within(dialog()).getByLabelText(/A travel group/));
    await userEvent.selectOptions(within(dialog()).getByLabelText("Group"), "g1");
    await userEvent.type(within(dialog()).getByLabelText("Title"), "Group hotel");
    await userEvent.click(within(dialog()).getByLabelText(/Also post this booking in the group chat/));
    await userEvent.upload(within(dialog()).getByLabelText(/Tickets \/ documents/), file("t.pdf", "application/pdf"));
    expect(within(dialog()).getByRole("list", { name: "Files to attach" })).toBeInTheDocument();
    await userEvent.click(within(dialog()).getByRole("button", { name: "Add booking" }));
    await waitFor(() => expect(createBooking).toHaveBeenCalled());
    expect(createBooking.mock.calls[0][0]).toMatchObject({ group_id: "g1", share_to_chat: true, title: "Group hotel" });
    expect(createBooking.mock.calls[0][0]).not.toHaveProperty("trip_id");
    expect(uploadBookingFile).toHaveBeenCalledWith("b2", expect.any(File));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(await screen.findByRole("link", { name: "Open t.pdf" })).toBeInTheDocument();
  });

  it("keeps the booking and explains when a file upload fails", async () => {
    listBookings.mockResolvedValue({ bookings: [] });
    createBooking.mockResolvedValue({ booking: BOOKING });
    const notFound = Object.assign(new Error("Not Found"), { status: 404 });
    uploadBookingFile.mockRejectedValue(notFound);
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Add booking/ }));
    await userEvent.selectOptions(within(dialog()).getByLabelText("Trip"), "t1");
    await userEvent.type(within(dialog()).getByLabelText("Title"), "Taj Resort");
    await userEvent.upload(within(dialog()).getByLabelText(/Tickets \/ documents/), file("t.pdf", "application/pdf"));
    await userEvent.click(within(dialog()).getByRole("button", { name: "Add booking" }));
    expect(await screen.findByText(/some files weren't attached/)).toBeInTheDocument();
    expect(screen.getByText(/update the backend and restart it/)).toBeInTheDocument();
    expect(screen.getByText("Taj Resort")).toBeInTheDocument();
  });

  it("blocks a wrong file type in the form before anything is sent", async () => {
    listBookings.mockResolvedValue({ bookings: [] });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Add booking/ }));
    await userEvent.upload(within(dialog()).getByLabelText(/Tickets \/ documents/), file("a.exe", "application/x-msdownload"), { applyAccept: false });
    expect(await within(dialog()).findByText(/isn't a PDF/)).toBeInTheDocument();
    expect(within(dialog()).queryByRole("list", { name: "Files to attach" })).not.toBeInTheDocument();
    expect(createBooking).not.toHaveBeenCalled();
  });

  it("lets the user drop a chosen file before saving", async () => {
    listBookings.mockResolvedValue({ bookings: [] });
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Add booking/ }));
    await userEvent.upload(within(dialog()).getByLabelText(/Tickets \/ documents/), file("t.pdf", "application/pdf"));
    await userEvent.click(within(dialog()).getByRole("button", { name: "Don't attach t.pdf" }));
    expect(within(dialog()).queryByRole("list", { name: "Files to attach" })).not.toBeInTheDocument();
  });
});
