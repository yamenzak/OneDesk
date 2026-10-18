frappe.provide("onedesk.places");

onedesk.places.heard = {};

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
			new Function("one", one.code)(listen);
		} catch (error) {
			onedesk.places.tripped(extension, error);
		}
	}
};

onedesk.places.emit = (key, data, powers, doctype = null) => {
	const heard = onedesk.places.heard[key];
	if (!heard || !heard.length) return;
	const [place, event] = key.split(".");
	const allowed = ((frappe.boot.one_places || {})[place] || {})[event] || [];
	for (const one of heard) {
		if (doctype && one.doctype && one.doctype !== doctype) continue;
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

onedesk.places.note = (text, tone) => {
	const kind = onedesk.places.TONES.includes(tone) ? tone : "gray";
	return $(`<div class="one-place-note one-place-note--${kind}"></div>`).text(String(text || ""));
};

onedesk.places.listening = (key) => !!(onedesk.places.heard[key] || []).length;

onedesk.places.spot = (put) => {
	const $spot = $(
		'<div class="one-place-spot"><div class="one-place-notes"></div><div class="one-place-actions"></div></div>'
	);
	put($spot);
	return {
		note: (text, tone) => $spot.find(".one-place-notes").append(onedesk.places.note(text, tone)),
		action: (label, handler) =>
			frappe.ui
				.button({ label: String(label || ""), variant: "subtle", onclick: () => handler() })
				.appendTo($spot.find(".one-place-actions")),
	};
};

onedesk.places.homes = () => {
	const Workspace = frappe.views && frappe.views.Workspace;
	if (!Workspace || Workspace.prototype.one_placed) return;
	Workspace.prototype.one_placed = true;
	const shown = Workspace.prototype.show_page;
	Workspace.prototype.show_page = async function (page) {
		const out = await shown.call(this, page);
		this.body.find(".one-place-spot").remove();
		if (!onedesk.places.listening("space.home") || !this._page) return out;
		const powers = onedesk.places.spot(($spot) => this.body.find(".editor-js-container").prepend($spot));
		onedesk.places.emit("space.home", { name: this._page.name, title: __(this._page.title) }, powers);
		return out;
	};
};

$(document).on("app_ready", () => {
	onedesk.places.load();
	onedesk.places.homes();
});
