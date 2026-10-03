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
			const params = frappe.utils.get_query_params();
			// OneCloud names its open folder and the file chosen in it; with a
			// file chosen its section is `file`, which is what it offers on.
			const cloud = onedesk.OneCloud && onedesk.OneCloud.here ? onedesk.OneCloud.here() : null;
			// A section that lists several records may be open on one of them, and
			// a page about one form (Customize) names it in its route.
			// OneMail names its open mailbox, folder and conversation the same way.
			return {
				doctype: "",
				name: "",
				page: route[0],
				section: params.section || (cloud && cloud.file ? "file" : ""),
				// A record's own calendar names it as ?doctype=&name=.
				record: params.type || params.rule || params.thread || (cloud && cloud.file) || params.name || route[1] || "",
				box: params.box || params.doctype || "",
				folder: params.folder || (cloud && cloud.folder) || "",
				view: "Page",
				label: (cloud && cloud.label) || document.title,
			};
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

// What is AI, drawn one way everywhere (oneai.css): frappe's own badge and
// button, with OneAI's mark in front and its spectrum round the edge. A tag
// says something OneAI does or did ("Read by OneAI"); a button asks it
// something, opening the panel on the question, which is the same question a
// suggestion on that page asks when there is one (so it runs the same way).
// A violet badge or a plain button standing in for either is the thing this
// replaces: one look, so a person learns it once.
onedesk.oneai.tag = (label, opts = {}) =>
	frappe.ui.badge.html({ ...opts, label, css_class: ["one-ai-tag", opts.css_class].filter(Boolean).join(" ") });

onedesk.oneai.button = (label, ask, opts = {}) =>
	frappe.ui.button.html({
		variant: "subtle",
		...opts,
		label,
		attrs: { ...(opts.attrs || {}), ...(ask ? { "data-one-ai-ask": ask } : {}) },
		css_class: ["one-ai-button", opts.css_class].filter(Boolean).join(" "),
	});

// Every OneAI button with a question asks it, wherever it is drawn. A button
// inside a dialog closes the dialog first: the panel is where the answer is.
$(document).on("click", "[data-one-ai-ask]", (event) => {
	event.preventDefault();
	const $button = $(event.currentTarget);
	const dialog = $button.closest(".modal");
	if (dialog.length) dialog.modal("hide");
	onedesk.oneai.open({ ask: $button.attr("data-one-ai-ask") });
});

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
				ask: __('What is "{0}" in {1} for? Suggest a value.', [
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
			.text(__("Was {0}", [one.was || __("empty")]))
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
			still ? __("Rewrite with {0}", [ONEAI]) : __("Write with {0}", [ONEAI]),
		);

	const mark = top.find(".one-ai-touched");
	if (still && !button.length && !mark.length) {
		$(`<img class="one-ai-touched" src="${MARK}" alt="${ONEAI}"
				title="${__("Written by {0}", [ONEAI])}">`).appendTo(top);
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

// ------------------------------------------------------------ the email window
//
// frappe's email window is a dialog, not a form, so `fields` never reaches its
// Message. The same mark goes beside it, and opens the same panel pointed at
// Communication's own `content` field: the same check on the way in
// (touch.target), the same card, the same Approve. Only where Approve lands
// differs: into the open window, beside the signature and the quoted message,
// which are kept as they are and are not OneAI's to write.

// frappe's own line between what is written and the message replied to
// (views/communication.js separator_regex).
const QUOTED = /<(?:div|p)(?:\s[^>]*)?>---<\/(?:div|p)>/i;

// Compared with every space taken out: a signature given as "Best,<br>Nadia"
// is two paragraphs by the time the editor has drawn it.
const squash = (value) => words(value).replace(/\s+/g, "");

onedesk.oneai.writing = null;

// The window's Message in three: what the writer wrote, their signature as the
// editor holds it, and the rest (frappe's separator and the quoted message).
onedesk.oneai.parts = function (writing) {
	const html = (writing && writing.composer.dialog.get_value("content")) || "";
	const at = html.search(QUOTED);
	const head = at < 0 ? html : html.slice(0, at);
	const rest = at < 0 ? "" : html.slice(at);
	const signed = squash(writing && writing.signature);
	// The editor hands its value back wrapped in its own `.ql-editor` div,
	// which is taken off here: its paragraphs are the lines.
	let $head = $("<div>").html(head);
	while ($head.children().length === 1 && $head.children(".ql-editor").length) $head = $head.children().first();
	const kids = $head.contents().toArray();
	let cut = kids.length;
	if (signed) {
		for (let i = kids.length - 1; i >= 0; i--) {
			const tail = squash(kids.slice(i).map((one) => one.textContent).join(""));
			if (tail === signed) {
				cut = i;
				break;
			}
			if (tail.length > signed.length) break;
		}
	}
	const html_of = (nodes) => nodes.map((one) => one.outerHTML || one.textContent).join("");
	// A blank line or two left between the text and the signature is spacing,
	// not writing.
	let end = cut;
	while (end > 0 && !words(kids[end - 1].textContent) && !$(kids[end - 1]).find("img").length) end--;
	return {
		written: html_of(kids.slice(0, end)),
		signature: html_of(kids.slice(end)),
		rest,
		quoted: rest ? words($("<div>").html(rest.replace(QUOTED, "")).text()) : "",
	};
};

// Put new text in the window, keeping its signature and quoted message.
onedesk.oneai.rewrite = function (html) {
	const writing = onedesk.oneai.writing;
	if (!writing || !writing.composer.dialog.display) return false;
	const parts = onedesk.oneai.parts(writing);
	// The editor draws paragraphs with no space between them, so an email's
	// are set apart by an empty line, as a person typing it would.
	const spaced = String(html || "").replace(/<\/p>\s*<p>/g, "</p><p><br></p><p>");
	writing.composer.dialog.set_value("content", spaced + (parts.signature || "") + (parts.rest || ""));
	return true;
};

// The email window beside the panel rather than under it (oneai.css).
onedesk.oneai.beside = function (on) {
	document.body.classList.toggle("one-ai-writing", !!on);
};

onedesk.oneai.compose = function (composer) {
	const field = composer.dialog && composer.dialog.fields_dict.content;
	const top = field && field.$wrapper.find(".clearfix").first();
	if (!top || !top.length || top.find(".one-ai-write").length) return;
	$(`<button type="button" class="one-ai-write" title="${__("Write with {0}", [ONEAI])}"><img src="${MARK}" alt="${ONEAI}"></button>`)
		.appendTo(top)
		.on("click", async (event) => {
			event.preventDefault();
			const sender = composer.dialog.get_value("sender") || "";
			let signature = "";
			try {
				signature = await composer.get_signature(sender);
			} catch (e) {
				signature = "";
			}
			const writing = { composer, signature };
			onedesk.oneai.writing = writing;
			const parts = onedesk.oneai.parts(writing);
			onedesk.oneai.beside(true);
			onedesk.oneai.open({
				field: {
					doctype: "Communication",
					name: "",
					fieldname: "content",
					label: __("Message"),
					value: parts.written,
					email: true,
					subject: composer.dialog.get_value("subject") || "",
					to: composer.dialog.get_value("recipients") || "",
					quoted: parts.quoted,
				},
			});
		});
	const hidden = composer.dialog.onhide;
	composer.dialog.onhide = function (...args) {
		if (onedesk.oneai.writing && onedesk.oneai.writing.composer === composer) {
			onedesk.oneai.writing = null;
			onedesk.oneai.beside(false);
		}
		return hidden && hidden.apply(this, args);
	};
};

(() => {
	const Composer = frappe.views && frappe.views.CommunicationComposer;
	if (!Composer || Composer.prototype.one_ai_made) return;
	const made = Composer.prototype.make;
	Composer.prototype.make = function (...args) {
		const out = made.apply(this, args);
		onedesk.oneai.compose(this);
		return out;
	};
	Composer.prototype.one_ai_made = true;
})();

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
