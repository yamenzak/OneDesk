// A record's head: the pill, the sentence, the band of numbers and charts, and the verbs
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
		onedesk.head.watch(frm.doctype);
	},
	refresh(frm) {
		onedesk.head.draw(frm);
		onedesk.head.linked(frm);
		// A workspace administrator customizes the form from its own menu
		// (one/customize.py). Frappe's own Customize is its System Managers'.
		if (!frm.meta.istable && !frm.meta.issingle && frappe.user.has_role("Workspace Administrator")) {
			frm.page.add_menu_item(__("Customize"), () => frappe.set_route("customize", frm.doctype), true);
		}
	},
});

onedesk.head.draw = (frm, drawn = null) => {
	frm.one_primary_verb = null;
	// A head that redraws as the form changes draws a new record from the form
	// as it stands; any other has nothing to say before the record is saved.
	if (!drawn && frm.is_new()) return onedesk.head.live(frm) && onedesk.head.preview(frm);
	const head = drawn || (frm.doc.__onload && frm.doc.__onload.one_head);
	// A form without a head is left as its own script drew it.
	if (!head && !frm.one_headed) return;
	frm.one_headed = !!head;
	// Only what this drew before goes: the message area is shared.
	frm.layout.message.children(".form-message:has(.one-head-sentence, .one-band), .one-record-changed").remove();
	if (!head) return;
	if (head.indicator) frm.page.set_indicator(head.indicator.label, head.indicator.colour);
	if (head.sentence) {
		// The framework writes "Submit this document to confirm" from
		// `show_submit_message`, after the refresh and stacking rather than
		// replacing. The sentence is that sentence with the answer in it, so it
		// goes after, in its place: frappe's own headline alert.
		const said = head.sentence;
		setTimeout(() => {
			frm.layout.message.children(".form-message:not(:has(.one-band))").remove();
			frm.dashboard.set_headline_alert(
				`<span class="one-head-sentence">${frappe.utils.escape_html(said.text)}</span>`,
				said.colour,
			);
		}, 0);
	}
	if (head.band.length || (head.charts || []).length) {
		onedesk.band.show(
			frm,
			head.band.map((one) => onedesk.band.stat(one.label, one.value, one.route, one.tone, one)),
			head.charts || [],
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
		if (!this.frm) return fields;
		onedesk.head.sections(this.frm.doctype).forEach((section, i) => {
			fields.splice(onedesk.head.place(fields, section.placed_in), 0, ...onedesk.head.drawn(this.frm.doctype)[i]);
		});
		return fields;
	};
	// And into the record's own copy of its fields, where frappe looks a
	// field up by name (the grid, set_df_property), as a custom field is.
	const copy_for = frappe.meta.make_docfield_copy_for;
	frappe.meta.make_docfield_copy_for = function (doctype, docname, docfield_list = null) {
		copy_for.call(this, doctype, docname, docfield_list);
		if (docfield_list) return;
		const copy = frappe.meta.docfield_copy[doctype][docname];
		for (const group of onedesk.head.drawn(doctype)) for (const df of group) copy[df.fieldname] = copy_dict(df);
	};
})();

// ------------------------------------------------------------------ redrawn as the form changes

onedesk.head.live = (frm) => (frappe.boot.one_heads_live || {})[frm.doctype];

// The head of the record as it stands in the form, unsaved (one/head.py,
// `preview`): a new record's, or a draft's once a field it reads changes.
onedesk.head.preview = frappe.utils.debounce(async (frm) => {
	const said = await frappe.xcall("onedesk.one.head.preview", { doc: frm.doc });
	if (said && frm === cur_frm) onedesk.head.draw(frm, said);
}, 300);

// The fields a live head reads: a change to one, or to any row of a table
// among them, redraws it.
onedesk.head.watched = new Set();
onedesk.head.watch = (doctype) => {
	const live = (frappe.boot.one_heads_live || {})[doctype];
	if (!live || onedesk.head.watched.has(doctype)) return;
	onedesk.head.watched.add(doctype);
	const redraw = (frm) => frm && frm.doctype === doctype && frm.doc.docstatus === 0 && onedesk.head.preview(frm);
	frappe.model.on(doctype, "*", (fieldname) => live.fields.includes(fieldname) && redraw(cur_frm));
	// A row removed is an event on the row's doctype, not the record's.
	for (const [table, child] of Object.entries(live.tables)) {
		frappe.model.on(child, "*", () => redraw(cur_frm));
		frappe.ui.form.on(child, { [`${table}_remove`]: redraw });
	}
};

onedesk.head.sections = (doctype) => (frappe.boot.one_linked || {})[doctype] || [];

// Each section as the fields frappe draws: a section break, then the linked
// record's fields under names of their own.
onedesk.head.drawn = (doctype) =>
	onedesk.head.sections(doctype).map((section) => [
		{ fieldtype: "Section Break", fieldname: `one_linked__${section.link_field}`, label: section.label, parent: doctype },
		...section.layout.map((df) => ({ ...df, read_only: 1, allow_on_submit: 1, parent: doctype })),
	]);

// At the end of the tab its field is in, which is before the next tab, or of
// the first tab when it names none.
onedesk.head.place = (fields, placed_in) => {
	const at = Math.max(placed_in ? fields.findIndex((df) => df.fieldname === placed_in) : 0, 0);
	const next = fields.findIndex((df, i) => i > at && df.fieldtype === "Tab Break");
	return next < 0 ? fields.length : next;
};

// Changing the link redraws its section.
onedesk.head.listened = new Set();
onedesk.head.listen = (doctype) => {
	if (onedesk.head.listened.has(doctype)) return;
	onedesk.head.listened.add(doctype);
	const events = {};
	for (const section of onedesk.head.sections(doctype)) events[section.link_field] = (frm) => onedesk.head.linked(frm);
	if (Object.keys(events).length) frappe.ui.form.on(doctype, events);
};

// What changed goes with the record however it is saved: frappe's one save
// runs for Save, Submit and Update alike, where no client event does (Update
// runs no validate), and an edit in a child table fires none of ours.
(() => {
	const saving = frappe.ui.form.save;
	frappe.ui.form.save = function (frm, ...rest) {
		onedesk.head.collect(frm);
		return saving.call(this, frm, ...rest);
	};
})();

// The fields a child row holds a value in, as the server reads them.
onedesk.head.columns = (doctype) =>
	frappe.meta
		.get_docfields(doctype)
		.filter((df) => !frappe.model.no_value_type.includes(df.fieldtype))
		.map((df) => df.fieldname);

// A table as it is sent: each row's values, and the name it has on the linked
// record, which a row added here has not.
onedesk.head.rows = (rows, doctype, own = (row) => row.__one_name) => {
	const columns = onedesk.head.columns(doctype);
	return (rows || []).map((row) => {
		const out = own(row) ? { name: own(row) } : {};
		for (const column of columns) out[column] = row[column] ?? null;
		return out;
	});
};

// Two tables are the same when their rows say the same, whatever null, empty
// or a number as text each side wrote.
onedesk.head.same = (a, b) => {
	const plain = (key, value) => (value === null || value === undefined ? "" : typeof value === "number" ? String(value) : value);
	return JSON.stringify(a, plain) === JSON.stringify(b, plain);
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
			const seen = shown && !one.hidden.includes(df.one_linked);
			if (seen && fresh) frm.doc[df.fieldname] = onedesk.head.fill(frm, df, one.values[df.one_linked]);
			field.df.hidden = seen ? 0 : 1;
			field.df.read_only = seen && !one.locked.includes(df.one_linked) ? 0 : 1;
			field.refresh();
		}
		// The section and the breaks that lay it out as the linked form does.
		for (const name of [`one_linked__${section.link_field}`, ...section.layout.filter((df) => !df.one_linked).map((df) => df.fieldname)]) {
			const part = frm.fields_dict[name];
			if (!part) continue;
			part.df.hidden = shown ? 0 : 1;
			part.refresh && part.refresh();
		}
		if (shown) onedesk.head.hear(one.doctype, one.name);
	}
	onedesk.head.collect(frm);
};

// A linked value as the form holds it. A child table's rows are copies under
// names of their own, so the linked record's own form, if it is open, keeps
// its rows; each remembers the name it has there.
onedesk.head.fill = (frm, df, value) => {
	if (df.fieldtype !== "Table" && df.fieldtype !== "Table MultiSelect") return value;
	return (value || []).map((row, i) => {
		const copy = {
			...row,
			doctype: df.options,
			name: `${df.fieldname}-${row.name}`,
			__one_name: row.name,
			parent: frm.doc.name,
			parenttype: frm.doctype,
			parentfield: df.fieldname,
			idx: i + 1,
			docstatus: 0,
		};
		frappe.model.add_to_locals(copy);
		return copy;
	});
};

// What the form sends with its own record: each linked record's changed
// values and the `modified` they were loaded at, or nothing. A table goes
// whole, as its form would send it.
onedesk.head.collect = (frm) => {
	const loaded = frm.one_linked_loaded || {};
	const sent = {};
	for (const section of onedesk.head.sections(frm.doctype)) {
		const one = loaded[section.link_field];
		if (!one || frm.doc[section.link_field] !== one.name) continue;
		const values = {};
		for (const df of section.fields) {
			if (one.hidden.includes(df.one_linked) || one.locked.includes(df.one_linked)) continue;
			const was = one.values[df.one_linked];
			if (df.fieldtype === "Table" || df.fieldtype === "Table MultiSelect") {
				const now = onedesk.head.rows(frm.doc[df.fieldname], df.options);
				if (!onedesk.head.same(now, onedesk.head.rows(was, df.options, (row) => row.name))) values[df.one_linked] = now;
				continue;
			}
			const now = frm.doc[df.fieldname];
			if (String(now ?? "") !== String(was ?? "")) values[df.one_linked] = now ?? null;
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
	onedesk.head.warn(
		frm,
		__("{0} {1} was changed by somebody else after you opened this. Refresh to see it.", [__(one.doctype), one.title]),
	);
};

// Somebody else saved the record, or a record it links to, while this form
// has unsaved changes: frappe-ui's row alert at the top of the form, the way
// the shell's pages say it, with Refresh.
onedesk.head.warn = (frm, title) => {
	frm.layout.message.children(".one-record-changed").remove();
	const $block = $(`<div class="form-message one-record-changed"></div>`).append(
		onedesk.shell.changed(title, () => frm.reload_doc()),
	);
	frm.layout.message.removeClass("hidden").prepend($block);
};

// Frappe's own warning for the record itself, drawn the same way rather than
// as a bootstrap button in a message. What it decides is frappe's.
frappe.ui.form.Form.prototype.show_conflict_message = function () {
	if (!this.doc.__needs_refresh) return;
	if (!this.doc.__unsaved) return this.debounced_reload_doc();
	onedesk.head.warn(this, __("This form has been modified after you have loaded it"));
};
