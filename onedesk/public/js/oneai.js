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
			// A settings page is a record named after its type, and its route
			// has no name in it.
			const single = !route[2] && frappe.get_meta(route[1]) && frappe.get_meta(route[1]).issingle;
			const name = route[2] || (single ? route[1] : "");
			// The label is the type as the reader calls it: a Deal, not an Opportunity.
			const called = __(route[1]);
			return { doctype: route[1], name, view: "Form", label: single ? called : `${called} ${name}`.trim() };
		}
		if (kind === "list" && route[1]) {
			const filters = window.cur_list && cur_list.get_filters_for_args ? cur_list.get_filters_for_args() : null;
			return {
				doctype: route[1],
				name: "",
				view: route[2] || "List",
				filters: filters && filters.length ? filters : null,
				label: __("{0} list", [__(route[1])]),
			};
		}
		if (kind === "query-report" && route[1]) {
			return { doctype: "", name: "", view: route[1], label: route[1] };
		}
		if (frappe.pages[route[0]]) {
			// A desk page has no record, so it is named by the page and the
			// part of it that is open, like Settings and its sections.
			const section = frappe.utils.get_query_params().section || "";
			return { doctype: "", name: "", page: route[0], section, view: "Page", label: document.title };
		}
		return null;
	},

	// The workspace home the reader is on, for what the panel offers there.
	// Not a page the model is told about — "the reader is on OneHR's home" is
	// noise to a model — only a key for the suggestions an employee starts on.
	home() {
		const route = frappe.get_route() || [];
		const kind = (route[0] || "").toLowerCase();
		return (kind === "workspaces" || kind === "workspace") && route[1] ? { workspace: route[1] } : null;
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

// Fields somebody writes prose in: where the control goes. The same list as
// `one_ai/touch.py`'s WRITES, which checks it again on the way in.
const PROSE = ["Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor"];

// Compared as words, because a Text Editor wraps what it is given in its own
// markup and would differ from what was written the moment it was drawn.
const words = (value) => $("<div>").html(String(value || "")).text().replace(/\s+/g, " ").trim();

onedesk.oneai.watched = new Set();

// The control beside each prose field, and the badge beside each one OneAI
// wrote. Run on every form refresh, which is when frappe has drawn its fields;
// both are skipped where they are already drawn.
onedesk.oneai.fields = function (frm) {
	if (!frm || !frm.fields_dict || frappe.session.user === "Guest") return;
	onedesk.oneai.landing(frm);
	onedesk.oneai.unchanged(frm);

	for (const field of frm.fields || []) {
		const df = field.df || {};
		if (frm.meta.issingle && !PROSE.includes(df.fieldtype)) onedesk.oneai.explain(frm, field);
		if (!PROSE.includes(df.fieldtype) || !field.$wrapper) continue;
		const top = field.$wrapper.find(".clearfix").first();
		if (!top.length) continue;

		// Asked of frappe's own rule rather than read off `disp_status`, which
		// `form-refresh` fires too early to find filled in on a first load.
		const writable = frappe.perm.get_field_display_status(df, frm.doc, frm.perm) === "Write";
		const drawn = top.find(".one-ai-write");
		if (writable && !drawn.length) {
			$(`<button type="button" class="one-ai-write"><img src="${MARK}" alt="${ONEAI}"></button>`)
				.appendTo(top)
				.on("click", (event) => {
					event.preventDefault();
					onedesk.oneai.open({
						field: {
							doctype: frm.doctype,
							name: frm.is_new() ? "" : frm.docname,
							fieldname: df.fieldname,
							label: __(df.label || df.fieldname),
							value: frm.doc[df.fieldname] || "",
						},
					});
				});
		} else if (!writable) {
			drawn.remove();
		}

		onedesk.oneai.badge(frm, df.fieldname);
		onedesk.oneai.watch(frm.doctype, df.fieldname);
	}
};

// On a settings page, every field a person may not know the meaning of gets a
// quiet mark beside its label, shown on hover: it asks OneAI what the field is
// for and what it should be here, with a card to set it if it should change —
// and, for a field pointing at records there are none of yet, the record first.
const ASKABLE = ["Check", "Select", "Link", "Data", "Int", "Float", "Currency", "Percent", "Duration", "Time", "Date", "Table MultiSelect", "Rating"];

onedesk.oneai.explain = function (frm, field) {
	const df = field.df || {};
	if (!ASKABLE.includes(df.fieldtype) || !field.$wrapper || df.hidden || df.read_only) return;
	const top = field.$wrapper.find(".clearfix, .checkbox label").first();
	if (!top.length || top.find(".one-ai-help").length) return;
	$(`<button type="button" class="one-ai-write one-ai-help" title="${__("Ask {0} about this", [ONEAI])}"><img src="${MARK}" alt="${ONEAI}"></button>`)
		.appendTo(top)
		.on("click", (event) => {
			event.preventDefault();
			event.stopPropagation(); // a check box's label would toggle it
			onedesk.oneai.open({
				about: df.fieldname,
				ask: __('What is "{0}" in {1} for, and what should it be set to here? If it should change, suggest the change.', [
					__(df.label || df.fieldname),
					__(frm.doctype),
				]),
			});
		});
};

// A change put into an open form: every field it touched is marked, with what
// it held before under it. The marks go when the form is saved or reloaded —
// `fields` runs on every refresh and clears them once nothing is unsaved.
onedesk.oneai.changed = function (frm, drawn) {
	for (const one of drawn) {
		const field = one.fieldname && frm.fields_dict[one.fieldname];
		if (!field || !field.$wrapper) continue;
		field.$wrapper.addClass("one-ai-changed");
		field.$wrapper.find(".one-ai-was").remove();
		$(`<div class="one-ai-was"></div>`)
			.text(__("was: {0}", [one.was || __("empty")]))
			.appendTo(field.$wrapper);
	}

	// A settings page is tabs, and the changes are rarely all on the one that is
	// open: each tab says how many it holds, and the page moves to the first of
	// them when the open one has none.
	const tabs = (frm.layout && frm.layout.tabs) || [];
	for (const tab of tabs) {
		const button = tab.tab_link.find(".nav-link");
		button.find(".one-ai-tab-count").remove();
		const count = tab.wrapper.find(".one-ai-changed").length;
		if (count) $(`<span class="one-ai-tab-count"></span>`).text(count).appendTo(button);
	}
	const open = tabs.find((tab) => tab.is_active());
	const first = tabs.find((tab) => tab.wrapper.find(".one-ai-changed").length);
	if (first && (!open || !open.wrapper.find(".one-ai-changed").length)) first.set_active();
};

onedesk.oneai.unchanged = function (frm) {
	if (frm.is_dirty()) return;
	frm.$wrapper.find(".one-ai-changed").removeClass("one-ai-changed");
	frm.$wrapper.find(".one-ai-was").remove();
	frm.$wrapper.find(".one-ai-tab-count").remove();
};

// One mark per field, and it is both things: the button that writes with
// OneAI, grey, and — in full colour — the sign that what the field says now is
// what OneAI wrote. An edit makes them differ and it goes grey again. A field
// the reader cannot write still shows the colour, as a mark with nothing to
// press.
onedesk.oneai.badge = function (frm, fieldname) {
	const field = frm.fields_dict[fieldname];
	if (!field || !field.$wrapper) return;
	const top = field.$wrapper.find(".clearfix").first();
	const written = ((frm.doc.__onload || {}).ai_touched || {})[fieldname];
	const still = written !== undefined && words(frm.doc[fieldname]) === words(written);

	const button = top.find(".one-ai-write");
	button
		.toggleClass("one-ai-write--wrote", still)
		.attr(
			"title",
			still ? __("Written by {0}. Press to write it again.", [ONEAI]) : __("Write with {0}", [ONEAI]),
		);

	const mark = top.find(".one-ai-touched");
	if (still && !button.length && !mark.length) {
		$(`<img class="one-ai-touched" src="${MARK}" alt="${ONEAI}"
				title="${__("Written by {0}. Goes once somebody edits it.", [ONEAI])}">`).appendTo(top);
	} else if (!still || button.length) {
		mark.remove();
	}
};

// Once per doctype and field, so an edit clears the badge as it is typed.
onedesk.oneai.watch = function (doctype, fieldname) {
	const key = `${doctype}:${fieldname}`;
	if (onedesk.oneai.watched.has(key)) return;
	onedesk.oneai.watched.add(key);
	frappe.model.on(doctype, fieldname, () => {
		if (window.cur_frm && cur_frm.doctype === doctype) onedesk.oneai.badge(cur_frm, fieldname);
	});
};

// A suggestion applied into this form. Remembered as written so the badge
// shows now, before any save; a new document has no name yet, so its changes
// wait for the save that gives it one.
onedesk.oneai.wrote = function (frm, changes, proposal) {
	if (frm.is_new()) {
		frm.__one_ai_landing = (frm.__one_ai_landing || []).concat(proposal);
		return;
	}
	frm.doc.__onload = frm.doc.__onload || {};
	frm.doc.__onload.ai_touched = { ...(frm.doc.__onload.ai_touched || {}), ...changes };
	onedesk.oneai.fields(frm);
};

onedesk.oneai.landing = function (frm) {
	const waiting = frm.__one_ai_landing;
	if (!waiting || !waiting.length || frm.is_new()) return;
	frm.__one_ai_landing = [];
	for (const proposal of waiting) {
		frappe
			.xcall("onedesk.one_ai.run.landed", { proposal, record: frm.docname })
			.then((kept) => {
				if (kept && Object.keys(kept).length) onedesk.oneai.wrote(frm, kept, proposal);
			})
			.catch(() => {});
	}
};

$(document).on("form-refresh", (event, frm) => onedesk.oneai.fields(frm));

$(document).on("app_ready", () => {
	onedesk.oneai.draw();
	onedesk.oneai.count();

	// The panel is told where the reader went rather than reading the route
	// itself, so the two never disagree about what "here" means.
	frappe.router.on("change", () => {
		if (onedesk.oneai.panel) onedesk.oneai.panel.moved(onedesk.oneai.where());
	});
});
