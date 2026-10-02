// Extensions on One's own pages: OneMail, OneCalendar and a record's head
// (one_studio/places.py says what each page has).
//
// frappe runs a Client Script on a form or a list; nothing runs one on a page
// of One's. So the extensions that are on come with the boot, each is run
// once here, and what it listens for is kept. A page then says what just
// happened on it (`onedesk.places.emit`), with a copy of what it shows and
// the few things an extension may do there; nothing else of the page is
// reachable. Every handler runs in a `try`: what one trips on is written down
// under its name (extensions.tripped) and the page goes on, as a form does.
frappe.provide("onedesk.places");

onedesk.places.heard = {};

// What an extension may do, by name. Each page builds these from its own
// parts; a page's event lends only the ones places.py lists for it.
onedesk.places.TONES = ["gray", "blue", "green", "orange", "red"];

onedesk.places.tripped = (extension, error) => {
	console.error(error);
	frappe
		.xcall("onedesk.one_studio.extensions.tripped", {
			extension,
			message: String((error && error.message) || error).slice(0, 500),
			stack: String((error && error.stack) || "").slice(0, 2000),
		})
		.catch(() => {});
};

onedesk.places.load = () => {
	const known = frappe.boot.one_places || {};
	for (const one of frappe.boot.one_page_extensions || []) {
		const [place] = String(one.place || "").split(".");
		if (!known[place]) continue;
		const extension = one.name;
		const listen = {
			on: (event, handler) => {
				// "conversation", or the place and its event as places.py names them.
				event = String(event || "").split(".").pop();
				if (!known[place][event] || typeof handler !== "function") return;
				const key = `${place}.${event}`;
				(onedesk.places.heard[key] = onedesk.places.heard[key] || []).push({
					extension,
					doctype: one.doctype,
					handler,
				});
			},
		};
		try {
			// The code passed its review as written (extensions.py boot keeps
			// only those), and runs as a Client Script's does, in the reader's
			// own browser with their own permissions.
			new Function("one", one.code)(listen);
		} catch (error) {
			onedesk.places.tripped(extension, error);
		}
	}
};

// `data` is copied before any extension sees it, so changing it changes
// nothing on the page; `powers` are the page's own functions, of which only
// those this event allows are lent.
onedesk.places.emit = (key, data, powers, doctype = null) => {
	const heard = onedesk.places.heard[key];
	if (!heard || !heard.length) return;
	const [place, event] = key.split(".");
	const allowed = ((frappe.boot.one_places || {})[place] || {})[event] || [];
	for (const one of heard) {
		// The head runs only the extensions written for its kind of record.
		if (doctype && one.doctype && one.doctype !== doctype) continue;
		// A function the extension hands the page, a button's handler, runs
		// later and is guarded the same way, under the same name.
		const guarded = (fn) => (...args) => {
			try {
				return fn(...args);
			} catch (error) {
				onedesk.places.tripped(one.extension, error);
			}
		};
		const page = {};
		for (const power of allowed) {
			if (powers[power])
				page[power] = (...args) => powers[power](...args.map((arg) => (typeof arg === "function" ? guarded(arg) : arg)));
		}
		Object.freeze(page);
		try {
			const out = one.handler(JSON.parse(JSON.stringify(data || {})), page);
			if (out && typeof out.catch === "function") out.catch((error) => onedesk.places.tripped(one.extension, error));
		} catch (error) {
			onedesk.places.tripped(one.extension, error);
		}
	}
};

// A note an extension shows, drawn as frappe-ui draws a small alert.
onedesk.places.note = (text, tone) => {
	const kind = onedesk.places.TONES.includes(tone) ? tone : "gray";
	return $(`<div class="one-place-note one-place-note--${kind}"></div>`).text(String(text || ""));
};

$(document).on("app_ready", () => onedesk.places.load());
