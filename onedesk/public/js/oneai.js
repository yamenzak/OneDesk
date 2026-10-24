frappe.provide("onedesk.oneai");

const MARK = "/assets/onedesk/images/oneai.svg";

const ONEAI = "OneAI";

onedesk.oneai = {
	dial: null,
	panel: null,
	waiting: 0,

	where() {
		const route = frappe.get_route() || [];
		const kind = (route[0] || "").toLowerCase();
		if (!route.length) return null;

		if (kind === "form" && route[1]) {
			const single = !route[2] && frappe.get_meta(route[1]) && frappe.get_meta(route[1]).issingle;
			const name = route[2] || (single ? route[1] : "");
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
				label: ((frappe.boot.one_titles || {}).DocType || {})[route[1]]
					? __(frappe.boot.one_titles.DocType[route[1]])
					: __("{0} list", [__(route[1])]),
			};
		}
		if (kind === "query-report" && route[1]) {
			const report = frappe.query_report;
			const shown = report && report.report_name === route[1] && report.get_filter_values ? report.get_filter_values(false) : null;
			return { doctype: "", name: "", report: route[1], view: "Report", filters: shown, label: __(route[1]) };
		}
		if (kind === "dashboard-view" && route[1]) {
			return { doctype: "", name: "", dashboard: route[1], view: "Dashboard", label: __(route[1]) };
		}
		if ((kind === "workspaces" || kind === "workspace") && route[1]) {
			return { doctype: "", name: "", workspace: route[1], view: "Workspace", label: __(route[1]) };
		}
		if (frappe.pages[route[0]]) {
			const params = frappe.utils.get_query_params();
			const cloud = onedesk.cloud && onedesk.cloud.here ? onedesk.cloud.here() : null;
			return {
				doctype: "",
				name: "",
				page: route[0],
				section: params.section || params.view || (cloud && cloud.file ? "file" : ""),
				record: params.type || params.rule || params.thread || params.reading || (cloud && cloud.file) || params.name || route[1] || "",
				box: params.box || params.doctype || "",
				folder: params.folder || (cloud && cloud.folder) || "",
				view: "Page",
				label: (cloud && cloud.label) || document.title,
			};
		}
		return null;
	},

	home() {
		const route = frappe.get_route() || [];
		const kind = (route[0] || "").toLowerCase();
		return (kind === "workspaces" || kind === "workspace") && route[1] ? { workspace: route[1] } : null;
	},

	async open(opening) {
		if (!onedesk.apps.ai()) return;
		if (!this.panel) {
			await frappe.require("oneai.bundle.js");
			this.panel = onedesk.oneai.mount(document.body);
		}
		this.panel.open(opening || (await this.inMail()) || this.justLeft() || {});
	},

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
		const said = this.waiting > 9 ? "9+" : String(this.waiting);
		$(".one-ai-row .one-bar-badge").text(said).toggleClass("hide", !this.waiting);
		if (!this.dial) return;
		const badge = this.dial.querySelector(".one-ai-dial__count");
		badge.textContent = said;
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

const PROSE = ["Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor"];

const words = (value) => $("<div>").html(String(value || "")).text().replace(/\s+/g, " ").trim();

onedesk.oneai.watched = new Set();

onedesk.oneai.fields = function (frm) {
	if (!frm || !frm.fields_dict || frappe.session.user === "Guest" || !onedesk.apps.ai()) return;
	onedesk.oneai.landing(frm);
	onedesk.oneai.unchanged(frm);

	onedesk.oneai.follow(frm);
	for (const field of frm.fields || []) {
		const df = field.df || {};
		if (!PROSE.includes(df.fieldtype) || !field.$wrapper) continue;
		onedesk.oneai.badge(frm, df.fieldname);
		onedesk.oneai.watch(frm.doctype, df.fieldname);
	}

	const touched = (frm.doc.__onload || {}).ai_touched || {};
	for (const fieldname of Object.keys(touched)) {
		const field = frm.fields_dict[fieldname];
		if (!field || PROSE.includes((field.df || {}).fieldtype)) continue;
		onedesk.oneai.badge(frm, fieldname);
		onedesk.oneai.watch(frm.doctype, fieldname);
	}
	onedesk.oneai.made(frm);
};

// A record OneAI suggested and somebody approved says so under who created
// it, as a record OneIntake made says so in its banner.
onedesk.oneai.made = function (frm) {
	const $side = frm.sidebar && frm.sidebar.sidebar ? frm.sidebar.sidebar : $();
	$side.find(".one-ai-made").remove();
	const made = (frm.doc.__onload || {}).ai_made;
	if (!made || frm.is_new()) return;
	$(`<li class="one-ai-made"></li>`)
		.html(onedesk.oneai.tag(__("Made by {0}", [ONEAI])))
		.attr("title", __("Suggested by {0} and approved by {1}", [ONEAI, made.by]))
		.insertAfter($side.find(".created-by").first());
};

onedesk.oneai.tag = (label, opts = {}) =>
	frappe.ui.badge.html({ ...opts, label, css_class: ["one-ai-tag", opts.css_class].filter(Boolean).join(" ") });

onedesk.oneai.button = (label, ask, opts = {}) =>
	!onedesk.apps.ai() ? "" : frappe.ui.button.html({
		variant: "subtle",
		...opts,
		label,
		attrs: { ...(opts.attrs || {}), ...(ask ? { "data-one-ai-ask": ask } : {}) },
		css_class: ["one-ai-button", opts.css_class].filter(Boolean).join(" "),
	});

$(document).on("click", "[data-one-ai-ask]", (event) => {
	event.preventDefault();
	const $button = $(event.currentTarget);
	const dialog = $button.closest(".modal");
	if (dialog.length) dialog.modal("hide");
	onedesk.oneai.open({ ask: $button.attr("data-one-ai-ask") });
});

// The field the reader was in when they opened the panel: a text field they
// may change is written into, any other is what the question is about. A
// field left more than a few seconds before is not meant.
const ASKABLE = ["Check", "Select", "Link", "Data", "Int", "Float", "Currency", "Percent", "Duration", "Time", "Date", "Table MultiSelect", "Rating"];
const JUST_LEFT_MS = 5000;

onedesk.oneai.follow = function (frm) {
	if (!frm.wrapper || frm.__one_ai_follows) return;
	frm.__one_ai_follows = true;
	$(frm.wrapper).on("focusout", "[data-fieldname]", (event) => {
		const fieldname = $(event.currentTarget).attr("data-fieldname");
		const df = (frm.fields_dict[fieldname] || {}).df;
		if (!df || df.hidden) return;
		const writable = frappe.perm.get_field_display_status(df, frm.doc, frm.perm) === "Write";
		const label = __(df.label || df.fieldname);
		if (PROSE.includes(df.fieldtype) && writable) {
			onedesk.oneai.left = { at: Date.now(), frm, field: { doctype: frm.doctype, name: frm.is_new() ? "" : frm.docname, fieldname, label, value: frm.doc[fieldname] || "" } };
		} else if (ASKABLE.includes(df.fieldtype)) {
			onedesk.oneai.left = { at: Date.now(), frm, about: { fieldname, label } };
		}
	});
};

onedesk.oneai.justLeft = function () {
	const left = onedesk.oneai.left;
	onedesk.oneai.left = null;
	if (!left || Date.now() - left.at > JUST_LEFT_MS || (left.frm && left.frm !== window.cur_frm)) return null;
	if (!left.field) return { about: left.about };
	return { field: left.frm ? { ...left.field, value: left.frm.doc[left.field.fieldname] || "" } : left.field };
};

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

onedesk.oneai.badge = function (frm, fieldname) {
	const field = frm.fields_dict[fieldname];
	if (!field || !field.$wrapper) return;
	const top = field.$wrapper.find(".clearfix").first();
	const written = ((frm.doc.__onload || {}).ai_touched || {})[fieldname];
	const still = written !== undefined && words(frm.doc[fieldname]) === words(written);

	const mark = top.find(".one-ai-touched");
	if (still && !mark.length) {
		$(`<img class="one-ai-touched" src="${MARK}" alt="${ONEAI}"
				title="${__("Written by {0}", [ONEAI])}">`).appendTo(top);
	} else if (!still) {
		mark.remove();
	}
};

onedesk.oneai.watch = function (doctype, fieldname) {
	const key = `${doctype}:${fieldname}`;
	if (onedesk.oneai.watched.has(key)) return;
	onedesk.oneai.watched.add(key);
	frappe.model.on(doctype, fieldname, () => {
		if (window.cur_frm && cur_frm.doctype === doctype) onedesk.oneai.badge(cur_frm, fieldname);
	});
};

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

const QUOTED = /<(?:div|p)(?:\s[^>]*)?>---<\/(?:div|p)>/i;

const squash = (value) => words(value).replace(/\s+/g, "");

onedesk.oneai.writing = null;

onedesk.oneai.parts = function (writing) {
	const html = (writing && writing.composer.dialog.get_value("content")) || "";
	const at = html.search(QUOTED);
	const head = at < 0 ? html : html.slice(0, at);
	const rest = at < 0 ? "" : html.slice(at);
	const signed = squash(writing && writing.signature);
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
	let end = cut;
	while (end > 0 && !words(kids[end - 1].textContent) && !$(kids[end - 1]).find("img").length) end--;
	return {
		written: html_of(kids.slice(0, end)),
		signature: html_of(kids.slice(end)),
		rest,
		quoted: rest ? words($("<div>").html(rest.replace(QUOTED, "")).text()) : "",
	};
};

onedesk.oneai.rewrite = function (html) {
	const writing = onedesk.oneai.writing;
	if (!writing || !writing.composer.dialog.display) return false;
	const parts = onedesk.oneai.parts(writing);
	const spaced = String(html || "").replace(/<\/p>\s*<p>/g, "</p><p><br></p><p>");
	writing.composer.dialog.set_value("content", spaced + (parts.signature || "") + (parts.rest || ""));
	return true;
};

onedesk.oneai.beside = function (on) {
	document.body.classList.toggle("one-ai-writing", !!on);
};

// An open mail window is what the panel writes in when it is opened: the
// dial shows above the window and nothing is drawn in it.
onedesk.oneai.compose = function (composer) {
	if (!onedesk.apps.ai() || !composer.dialog) return;
	onedesk.oneai.composing = composer;
	document.body.classList.add("one-ai-composing");
	const hidden = composer.dialog.onhide;
	composer.dialog.onhide = function (...args) {
		if (onedesk.oneai.composing === composer) {
			onedesk.oneai.composing = null;
			document.body.classList.remove("one-ai-composing");
		}
		if (onedesk.oneai.writing && onedesk.oneai.writing.composer === composer) {
			onedesk.oneai.writing = null;
			onedesk.oneai.beside(false);
		}
		return hidden && hidden.apply(this, args);
	};
};

onedesk.oneai.inMail = async function () {
	const composer = onedesk.oneai.composing;
	if (!composer || !composer.dialog.display) return null;
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
	return {
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
	if (!onedesk.apps.ai()) return;
	onedesk.oneai.draw();
	onedesk.oneai.count();

	frappe.router.on("change", () => {
		if (onedesk.oneai.panel) onedesk.oneai.panel.moved(onedesk.oneai.where());
	});
});
