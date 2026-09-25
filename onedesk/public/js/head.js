// A record's head: the pill, the sentence, the band of numbers and the verbs
// above its fields, drawn from what the server worked out as the reader
// (one/head.py, `__onload.one_head`). One renderer for every doctype with a
// Record Head; nothing here knows any of them. docs/SHELL.md, decision 4.
// Below them, its linked sections: fields of a record it links to, edited in
// frappe's own controls and saved with it (one/linked.py, decision 5).
frappe.provide("onedesk.head");

frappe.ui.form.on("*", {
	setup(frm) {
		// ERPNext's own refresh, which runs after ours, makes Create the primary
		// group. While a primary verb is on the page it is the one dark button.
		const primary = frm.page.set_inner_btn_group_as_primary.bind(frm.page);
		frm.page.set_inner_btn_group_as_primary = (label) =>
			frm.one_primary_verb && frm.custom_buttons[frm.one_primary_verb] ? null : primary(label);
		onedesk.head.listen(frm.doctype);
	},
	refresh(frm) {
		onedesk.head.draw(frm);
		onedesk.head.linked(frm);
	},
});

onedesk.head.draw = (frm) => {
	frm.one_primary_verb = null;
	const head = !frm.is_new() && frm.doc.__onload && frm.doc.__onload.one_head;
	// A form without a head is left as its own script drew it.
	if (!head && !frm.one_headed) return;
	frm.one_headed = !!head;
	// Only what this drew before goes: the message area is shared.
	frm.layout.message.children(".form-message:has(.one-head-sentence, .one-band, .one-linked-changed)").remove();
	if (!head) return;
	if (head.indicator) frm.page.set_indicator(head.indicator.label, head.indicator.colour);
	if (head.sentence) {
		frm.dashboard.set_headline(
			`<div class="one-head-sentence">${frappe.utils.escape_html(head.sentence.text)}</div>`,
			head.sentence.colour,
			true,
		);
	}
	if (head.band.length) {
		onedesk.band.show(
			frm,
			head.band.map((one) => onedesk.band.stat(one.label, one.value, one.route, one.tone)),
		);
	}
	for (const verb of head.verbs) {
		frm.add_custom_button(verb.label, () => onedesk.head.act(frm, verb));
		if (verb.primary) {
			frm.change_custom_button_type(verb.label, null, "primary");
			frm.one_primary_verb = verb.label;
		}
	}
};

// A verb asks what it needs in frappe's own dialog, then the server does it,
// checking again that it still can be done.
onedesk.head.act = (frm, verb) => {
	const go = (values) =>
		frappe
			.xcall("onedesk.one.head.run", { doctype: frm.doctype, name: frm.doc.name, verb: verb.verb, values })
			.then((message) => {
				frappe.ui.toast({ message, type: "success" });
				frm.reload_doc();
			});
	if (!verb.fields.length) return go({});
	const dialog = new frappe.ui.Dialog({
		title: verb.title,
		fields: verb.fields,
		primary_action_label: verb.action,
		primary_action(values) {
			dialog.disable_primary_action();
			go(values)
				.then(() => dialog.hide())
				.finally(() => dialog.enable_primary_action());
		},
	});
	dialog.show();
};

// ------------------------------------------------------------------ linked sections

// The sections go into the form's layout where frappe builds it, each a
// section of frappe's own controls, read-only until the record is loaded.
(() => {
	const Layout = frappe.ui.form.Layout;
	const fields_of = Layout.prototype.get_doctype_fields;
	Layout.prototype.get_doctype_fields = function () {
		const fields = fields_of.call(this);
		const sections = (this.frm && onedesk.head.sections(this.frm.doctype)) || [];
		for (const section of sections) {
			fields.splice(
				onedesk.head.place(fields, section.placed_in),
				0,
				{ fieldtype: "Section Break", fieldname: `one_linked__${section.link_field}`, label: section.label },
				...section.fields.map((df) => ({ ...df, read_only: 1, allow_on_submit: 1 })),
			);
		}
		return fields;
	};
})();

onedesk.head.sections = (doctype) => (frappe.boot.one_linked || {})[doctype] || [];

// At the end of the tab its field is in, which is before the next tab, or of
// the first tab when it names none.
onedesk.head.place = (fields, placed_in) => {
	const at = Math.max(placed_in ? fields.findIndex((df) => df.fieldname === placed_in) : 0, 0);
	const next = fields.findIndex((df, i) => i > at && df.fieldtype === "Tab Break");
	return next < 0 ? fields.length : next;
};

// Each linked field says what changed as it changes, since frappe runs no
// validate on Update; the link itself redraws its section.
onedesk.head.listened = new Set();
onedesk.head.listen = (doctype) => {
	if (onedesk.head.listened.has(doctype)) return;
	onedesk.head.listened.add(doctype);
	const events = {};
	for (const section of onedesk.head.sections(doctype)) {
		events[section.link_field] = (frm) => onedesk.head.linked(frm);
		for (const df of section.fields) events[df.fieldname] = (frm) => onedesk.head.collect(frm);
	}
	if (Object.keys(events).length) frappe.ui.form.on(doctype, events);
};

// Fill each section from the record as loaded, and say who may change what.
// A section shows only while the record links where it did when it loaded:
// its fields belong to that record, not to one just picked.
onedesk.head.linked = (frm) => {
	const sections = onedesk.head.sections(frm.doctype);
	if (!sections.length) return;
	const head = !frm.is_new() && frm.doc.__onload && frm.doc.__onload.one_head;
	const loaded = (head && head.linked) || {};
	const fresh = frm.one_linked_loaded !== loaded;
	frm.one_linked_loaded = loaded;
	for (const section of sections) {
		const one = loaded[section.link_field];
		const shown = !!one && frm.doc[section.link_field] === one.name;
		for (const df of section.fields) {
			const field = frm.fields_dict[df.fieldname];
			if (!field) continue;
			if (shown && fresh) frm.doc[df.fieldname] = one.values[df.one_linked];
			field.df.hidden = shown ? 0 : 1;
			field.df.read_only = shown && !one.locked.includes(df.one_linked) ? 0 : 1;
			field.refresh();
		}
		const part = frm.fields_dict[`one_linked__${section.link_field}`];
		if (part) {
			part.df.hidden = shown ? 0 : 1;
			part.refresh();
		}
		if (shown) onedesk.head.hear(one.doctype, one.name);
	}
	onedesk.head.collect(frm);
};

// What the form sends with its own record: each linked record's changed
// values and the `modified` they were loaded at, or nothing.
onedesk.head.collect = (frm) => {
	const loaded = frm.one_linked_loaded || {};
	const sent = {};
	for (const section of onedesk.head.sections(frm.doctype)) {
		const one = loaded[section.link_field];
		if (!one || frm.doc[section.link_field] !== one.name) continue;
		const values = {};
		for (const df of section.fields) {
			const now = frm.doc[df.fieldname];
			if (String(now ?? "") !== String(one.values[df.one_linked] ?? "")) values[df.one_linked] = now ?? null;
		}
		if (Object.keys(values).length) sent[section.link_field] = { name: one.name, modified: one.modified, values };
	}
	if (Object.keys(sent).length) frm.doc.__one_linked = sent;
	else delete frm.doc.__one_linked;
};

// A linked record somebody else saved: as frappe does for the record itself,
// reload when nothing here is unsaved, and say so when something is.
onedesk.head.heard = new Set();
onedesk.head.hear = async (doctype, name) => {
	const key = `${doctype}:${name}`;
	if (onedesk.head.heard.has(key)) return;
	onedesk.head.heard.add(key);
	// Heard from the first subscription on: when this script loads, frappe's
	// socket is not there yet to listen on.
	if (!onedesk.head.listening) {
		onedesk.head.listening = true;
		frappe.realtime.on("doc_update", onedesk.head.updated);
	}
	// frappe lets one subscription through a second; wait our turn.
	while (frappe.flags.doc_subscribe) await new Promise((done) => setTimeout(done, 250));
	frappe.realtime.doc_subscribe(doctype, name);
};

onedesk.head.updated = (data) => {
	const frm = window.cur_frm;
	if (!frm || frappe.get_route()[0] !== "Form" || frappe.ui.form.is_saving) return;
	const one = Object.values(frm.one_linked_loaded || {}).find((it) => it.doctype === data.doctype && it.name === data.name);
	if (!one || !data.modified || data.modified === one.modified) return;
	if (!frm.is_dirty()) return frm.debounced_reload_doc();
	frm.layout.message.children(".form-message:has(.one-linked-changed)").remove();
	frm.dashboard.set_headline(
		`<div class="one-linked-changed">${frappe.utils.escape_html(
			__("{0} {1} was changed by somebody else after you opened this. Refresh to see it.", [__(one.doctype), one.title]),
		)}</div>`,
		"yellow",
		true,
	);
	const $refresh = $(onedesk.shell.button(__("Refresh"), {}, "ghost")).on("click", () => frm.reload_doc());
	frm.layout.message.children(".form-message:has(.one-linked-changed)").find(".one-linked-changed").append($refresh);
};
