/**
 * Two people in one workbook or document, over the socket the bench already runs.
 *
 * Frappe's socketio process loads apps/<app>/realtime/handlers.js and calls it
 * once a connection (frappe/realtime/index.js), so this needs no second
 * service. A message goes browser → node → browsers and never touches Python;
 * Python is asked once a room a socket, `admit`: who this is, and whether they
 * may write. After OneApp's realtime/handlers.js. onedesk/one_sheet/AGENTS.md.
 */

// What a client may ask to join; what each means is one_sheet/live.py's.
const KINDS = new Set(["workbook", "document"]);

// Events a reader may send: asking for the state, being seen, and a
// document's comments, which reading is enough for. Changing cells or text,
// or answering with a whole state, needs the right to write.
const READERS_MAY = new Set(["yjs_state_request", "yjs_awareness", "yjs_awareness_bye", "yjs_comments"]);

const MAX_BYTES = 2 * 1024 * 1024;

// What a phone remote and the presenter view it drives may say to each other.
const REMOTE_SAYS = new Set(["hello", "go", "point", "state"]);
const BURST = 300;
const WINDOW_MS = 5000;

const roomName = (kind, name) => `onedesk:${kind}/${name}`;

function onedesk_handlers(socket) {
	const joined = new Map();
	let sent = 0;
	let windowStarted = Date.now();

	function allowed() {
		const now = Date.now();
		if (now - windowStarted > WINDOW_MS) {
			windowStarted = now;
			sent = 0;
		}
		return ++sent <= BURST;
	}

	socket.on("onedesk_join", async (kind, name, ack) => {
		const reply = typeof ack === "function" ? ack : () => {};
		if (!KINDS.has(kind) || !name) return reply({ ok: false });
		try {
			const res = await socket.frappe_request("/api/method/onedesk.one_sheet.live.admit", { kind, name });
			const { message } = await res.json();
			if (!message || !message.ok) return reply({ ok: false });
			// The room the server named, never the one the client asked for.
			const room = roomName(kind, message.name);
			socket.onedesk_who = message.who;
			joined.set(room, { write: !!message.write });
			socket.join(room);
			reply({ ok: true, room, write: !!message.write, who: message.who });
		} catch (err) {
			console.warn("onedesk_join failed", err);
			reply({ ok: false });
		}
	});

	socket.on("onedesk_send", (room, event, payload) => {
		const seat = joined.get(room);
		if (!seat || !event || !(seat.write || READERS_MAY.has(event)) || !allowed()) return;
		let body;
		try {
			body = JSON.stringify(payload ?? null);
		} catch {
			return;
		}
		if (body.length > MAX_BYTES) return;
		// Who somebody is comes from admit, not from what their browser says.
		if (event === "yjs_awareness" && payload && payload.state && typeof payload.state === "object" && socket.onedesk_who) {
			const who = socket.onedesk_who;
			payload.state.user = { ...(payload.state.user || {}), id: who.user, fullName: who.fullName, image: who.image };
		}
		// To everybody else: echoing a change back to its sender doubles it.
		socket.to(room).emit("onedesk_said", { room, event, payload });
	});

	socket.on("onedesk_leave", (room) => {
		if (!joined.has(room)) return;
		joined.delete(room);
		socket.leave(room);
	});

	// A OneDisplay screen joins by its token, never by a cookie: it is
	// nobody. It only hears; the rooms are the ones live.admit names.
	socket.on("onedesk_display_join", async (screen, token, ack) => {
		const reply = typeof ack === "function" ? ack : () => {};
		if (!screen || !token) return reply({ ok: false });
		try {
			const res = await socket.frappe_request("/api/method/onedesk.one_display.live.admit", { screen, token });
			const { message } = await res.json();
			if (!message || !message.ok) return reply({ ok: false });
			for (const room of message.rooms || []) {
				if (room.startsWith("onedesk:display/")) socket.join(room);
			}
			reply({ ok: true });
		} catch (err) {
			console.warn("onedesk_display_join failed", err);
			reply({ ok: false });
		}
	});

	// A guest on a presentation's link joins by the ticket its page was given
	// once it passed the link's gates (only the session's cookie reaches
	// frappe_request); it only hears where the presenter is (one_slide/shared.py).
	socket.on("onedesk_slide_join", async (token, item, ticket, ack) => {
		const reply = typeof ack === "function" ? ack : () => {};
		if (!token || !ticket) return reply({ ok: false });
		try {
			const res = await socket.frappe_request("/api/method/onedesk.one_slide.shared.admit", { token, item: item || "", ticket });
			const { message } = await res.json();
			if (!message || !message.ok) return reply({ ok: false });
			for (const room of message.rooms || []) {
				if (room.startsWith("onedesk:slide/")) socket.join(room);
			}
			reply({ ok: true });
		} catch (err) {
			console.warn("onedesk_slide_join failed", err);
			reply({ ok: false });
		}
	});

	// A phone and the screen it drives (the presenter view, or a page showing
	// a presentation through a link) meet in the room of the phone's token,
	// each with its own key (one_slide/remote.py admit). Only what a remote
	// says passes, small, and never back to whoever said it.
	socket.on("onedesk_remote_join", async (token, key, ack) => {
		const reply = typeof ack === "function" ? ack : () => {};
		if (!token || !key) return reply({ ok: false });
		try {
			const res = await socket.frappe_request("/api/method/onedesk.one_slide.remote.admit", { token, key });
			const { message } = await res.json();
			if (!message || !message.ok || !String(message.room).startsWith("onedesk:remote/")) return reply({ ok: false, taken: !!(message && message.taken) });
			socket.onedesk_remote = message.room;
			socket.join(message.room);
			reply({ ok: true });
		} catch (err) {
			console.warn("onedesk_remote_join failed", err);
			reply({ ok: false });
		}
	});

	socket.on("onedesk_remote_say", (event, payload) => {
		const room = socket.onedesk_remote;
		if (!room || !REMOTE_SAYS.has(event) || !allowed()) return;
		let body;
		try {
			body = JSON.stringify(payload ?? null);
		} catch {
			return;
		}
		if (body.length > 4096) return;
		socket.to(room).emit("onedesk_remote", { event, payload });
	});

	socket.on("disconnect", () => joined.clear());
}

module.exports = onedesk_handlers;
