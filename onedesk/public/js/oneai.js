frappe.provide("onedesk.oneai");

// The launcher, and only the launcher.
//
// This file is in `app_include_js`, so it is on every desk page and its whole
// job is to be small: a button, the badge on it, and the route the panel will
// be told about. The panel itself is a Vue island in `oneai.bundle.js` and is
// not fetched until somebody opens it — the same lazy shape frappe uses for its
// own file uploader, and the reason a bundle with Vue in it costs nothing on a
// page nobody asks OneAI anything on.
//
// The button is appended to `body` rather than to the page container. That is
// what makes a conversation survive moving between records: frappe tears the
// page down on every route change and would take the panel with it.

const MARK = "/assets/onedesk/images/oneai.svg";

// A product name is a name: the same in every language, so it is never wrapped
// in `__()` and is written down once.
const ONEAI = "OneAI";

// Routes with nothing to point at. A workspace is a place rather than a record,
// and "the reader is on the Workspaces page" is not context, it is noise.
const NOWHERE = ["workspace", "workspaces", "dashboard-view"];

onedesk.oneai = {
	dial: null,
	panel: null,
	waiting: 0,

	// Where the reader is, as a pointer. Never the record's values: the panel
	// sends this to a model that has `read_record`, and that reads as whoever
	// is signed in, so a pointer at something they may not see buys nothing.
	where() {
		const route = frappe.get_route() || [];
		const kind = (route[0] || "").toLowerCase();
		if (!route.length || NOWHERE.includes(kind)) return null;

		if (kind === "form" && route[1]) {
			return { doctype: route[1], name: route[2] || "", view: "Form", label: `${route[1]} ${route[2] || ""}`.trim() };
		}
		if (kind === "list" && route[1]) {
			const filters = window.cur_list && cur_list.get_filters_for_args ? cur_list.get_filters_for_args() : null;
			return {
				doctype: route[1],
				name: "",
				view: route[2] || "List",
				filters: filters && filters.length ? filters : null,
				label: __("{0} list", [route[1]]),
			};
		}
		if (kind === "query-report" && route[1]) {
			return { doctype: "", name: "", view: route[1], label: route[1] };
		}
		return null;
	},

	async open(opening) {
		if (!this.panel) {
			await frappe.require("oneai.bundle.js");
			this.panel = onedesk.oneai.mount(document.body);
		}
		this.panel.open(opening || {});
	},

	// What is suggested and unanswered, shown on the button so a card parked by
	// a run somebody closed the panel on is still visible from anywhere.
	async count() {
		if (!frappe.session.user || frappe.session.user === "Guest") return;
		try {
			const waiting = await frappe.xcall("onedesk.one_ai.run.waiting");
			this.waiting = (waiting || []).length;
		} catch (e) {
			this.waiting = 0;
		}
		this.paint();
	},

	paint() {
		if (!this.dial) return;
		const badge = this.dial.querySelector(".one-ai-dial__count");
		badge.textContent = this.waiting > 9 ? "9+" : String(this.waiting);
		badge.hidden = !this.waiting;
	},

	draw() {
		if (this.dial || frappe.session.user === "Guest") return;
		const dial = document.createElement("button");
		dial.className = "one-ai-dial";
		dial.type = "button";
		dial.title = __("Ask {0}", [ONEAI]);
		dial.setAttribute("aria-label", __("Ask {0}", [ONEAI]));
		dial.innerHTML = `
			<span class="one-ai-dial__face"><img src="${MARK}" alt=""></span>
			<span class="one-ai-dial__count" hidden></span>`;
		dial.addEventListener("click", () => this.open());
		document.body.appendChild(dial);
		this.dial = dial;
		this.paint();
	},
};

$(document).on("app_ready", () => {
	onedesk.oneai.draw();
	onedesk.oneai.count();

	// The panel is told where the reader went rather than reading the route
	// itself, so the two never disagree about what "here" means.
	frappe.router.on("change", () => {
		if (onedesk.oneai.panel) onedesk.oneai.panel.moved(onedesk.oneai.where());
	});
});
