frappe.provide("onedesk.head");

frappe.ui.form.on("*", {
	setup(frm) {
		const primary = frm.page.set_inner_btn_group_as_primary.bind(frm.page);
		frm.page.set_inner_btn_group_as_primary = (label) =>
			frm.one_primary_verb && frm.custom_buttons[frm.one_primary_verb] ? null : primary(label);
		onedesk.head.listen(frm.doctype);
		onedesk.head.watch(frm.doctype);
	},
	refresh(frm) {
		onedesk.head.draw(frm);
		onedesk.head.extended(frm);
		onedesk.head.linked(frm);
		if (!frm.meta.istable && !frm.meta.issingle && frappe.user.has_role("Workspace Administrator")) {
			frm.page.add_menu_item(
				__("Custom Fields"),
				() => frappe.set_route("List", "Workspace Field", { form: frm.doctype }),
				true,
			);
		}
		if (onedesk.doctype_settings.offered(frm.meta)) {
			frm.page.add_menu_item(__("Settings"), () => onedesk.doctype_settings.open(frm.doctype), true);
		}
	},
});

onedesk.head.extended = (frm) => {
	if (frm.is_new() || !frm.one_headed || !onedesk.places) return;
	const head = (frm.doc.__onload && frm.doc.__onload.one_head) || {};
	const figures = [];
	const record = {};
	for (const [key, value] of Object.entries(frm.doc)) if (!key.startsWith("__")) record[key] = value;
	const TONE = { gray: "gray", blue: "blue", green: "green", orange: "orange", red: "red" };
	onedesk.places.emit(
		"record_head.drawn",
		record,
		{
			verb: (label, handler) => frm.add_custom_button(String(label || ""), () => handler()),
			figure: (label, value) => figures.push({ label: String(label || ""), value: String(value ?? "") }),
			note: (text, tone) =>
				frm.dashboard.add_comment(frappe.utils.escape_html(String(text || "")), TONE[tone] || "gray", true),
		},
		frm.doctype
	);
	if (!figures.length) return;
	onedesk.band.show(
		frm,
		[...(head.band || []), ...figures].map((one) => onedesk.band.stat(one.label, one.value, one.route, one.tone, one)),
		head.charts || []
	);
};

onedesk.head.draw = (frm, drawn = null) => {
	frm.one_primary_verb = null;
	if (!drawn && frm.is_new()) return onedesk.head.live(frm) && onedesk.head.preview(frm);
	const head = drawn || (frm.doc.__onload && frm.doc.__onload.one_head);
	if (!head && !frm.one_headed) return;
	frm.one_headed = !!head;
	frm.layout.message.children(".form-message:has(.one-head-sentence, .one-band), .one-record-changed, .one-notice").remove();
	if (!head) return;
	for (const notice of head.notices || []) onedesk.head.notice(frm, notice);
	if (head.indicator) frm.page.set_indicator(head.indicator.label, head.indicator.colour);
	if (head.sentence) {
		const said = head.sentence;
		setTimeout(() => {
			frm.layout.message.children(".form-message:not(:has(.one-band))").not(frm.$intro_message || []).remove();
			frm.dashboard.set_headline_alert(
				`<span class="one-head-sentence">${frappe.utils.escape_html(said.text)}</span>`,
				said.colour === "gray" ? "white" : said.colour,
				true,
			);
			frm.layout.message.children(".form-message:has(.one-head-sentence)").prependTo(frm.layout.message);
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
		frm.add_custom_button(verb.label, () => onedesk.head.act(frm, verb), verb.group || undefined);
		if (verb.primary && !verb.group) {
			frm.change_custom_button_type(verb.label, null, "primary");
			frm.one_primary_verb = verb.label;
		}
	}
};

onedesk.head.notice = (frm, notice) => {
	const $notice = $(`<div class="form-message one-notice ${notice.colour}"><div class="one-notice-text"></div><div class="one-notice-verbs"></div></div>`);
	$notice.find(".one-notice-text").text(notice.text);
	for (const line of notice.lines || []) $("<div>").text(line).appendTo($notice.find(".one-notice-text"));
	for (const verb of notice.verbs) {
		$notice.find(".one-notice-verbs").append(frappe.ui.button({ label: verb.label, variant: "subtle", onclick: () => onedesk.head.act(frm, verb) }));
	}
	frm.layout.message.append($notice).removeClass("hidden");
};

onedesk.head.act = (frm, verb) => {
	const go = (values) =>
		frappe
			.xcall("onedesk.one.head.run", { doctype: frm.doctype, name: frm.doc.name, verb: verb.verb, values })
			.then((message) => {
				frappe.ui.toast({ message, type: "success" });
				frm.reload_doc();
			});
	if (!verb.fields.length) return go({});
	const redraw = frappe.utils.debounce(() => onedesk.head.redraw(frm, verb, dialog), 250);
	const fields = verb.live ? onedesk.head.foreseen(verb.fields, redraw) : verb.fields;
	const dialog = new frappe.ui.Dialog({
		title: verb.title,
		fields,
		primary_action_label: verb.action,
		primary_action(values) {
			dialog.disable_primary_action();
			go(values)
				.then(() => dialog.hide())
				.finally(() => dialog.enable_primary_action());
		},
	});
	dialog.show();
	if (verb.live) redraw();
};

onedesk.head.foreseen = (fields, redraw) => {
	const placed = fields.find((df) => df.fieldname === "one_live");
	const table = {
		fieldname: "one_live",
		fieldtype: "Table",
		label: placed?.label || __("Effect"),
		hidden: 1,
		read_only: 1,
		cannot_add_rows: 1,
		cannot_delete_rows: 1,
		in_place_edit: true,
		data: [],
		fields: [
			{ fieldname: "label", fieldtype: "Data", label: __("Figure"), in_list_view: 1, read_only: 1, columns: 4 },
			{ fieldname: "now", fieldtype: "Currency", label: __("Current"), in_list_view: 1, read_only: 1, columns: 3 },
			{ fieldname: "after", fieldtype: "Currency", label: __("After"), in_list_view: 1, read_only: 1, columns: 3 },
		],
	};
	const said = { fieldname: "one_live_said", fieldtype: "HTML" };
	const rest = fields.filter((df) => df.fieldname !== "one_live").map((df) => ({ ...df, onchange: redraw }));
	if (!placed) return [...rest, table, said];
	const at = fields.indexOf(placed);
	return [...rest.slice(0, at), table, said, ...rest.slice(at)];
};

onedesk.head.redraw = async (frm, verb, dialog) => {
	const said = await frappe.xcall("onedesk.one.head.foresee", { doctype: frm.doctype, name: frm.doc.name, verb: verb.verb, values: dialog.get_values(true) });
	const field = dialog.fields_dict.one_live;
	const rows = said?.rows || [];
	field.df.data = rows.map((row) => ({ ...row }));
	field.grid.refresh();
	dialog.set_df_property("one_live", "hidden", rows.length ? 0 : 1);
	const $said = dialog.fields_dict.one_live_said.$wrapper.empty();
	if (rows.length && said.lines?.length) $("<p class=\"help-box small text-muted\">").text(said.lines.join(" ")).appendTo($said);
};

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
	const copy_for = frappe.meta.make_docfield_copy_for;
	frappe.meta.make_docfield_copy_for = function (doctype, docname, docfield_list = null) {
		copy_for.call(this, doctype, docname, docfield_list);
		if (docfield_list) return;
		const copy = frappe.meta.docfield_copy[doctype][docname];
		for (const group of onedesk.head.drawn(doctype)) for (const df of group) copy[df.fieldname] = copy_dict(df);
	};
})();

onedesk.head.live = (frm) => (frappe.boot.one_heads_live || {})[frm.doctype];

onedesk.head.preview = frappe.utils.debounce(async (frm) => {
	const said = await frappe.xcall("onedesk.one.head.preview", { doc: frm.doc });
	if (said && frm === cur_frm) onedesk.head.draw(frm, said);
}, 300);

onedesk.head.watched = new Set();
onedesk.head.watch = (doctype) => {
	const live = (frappe.boot.one_heads_live || {})[doctype];
	if (!live || onedesk.head.watched.has(doctype)) return;
	onedesk.head.watched.add(doctype);
	const redraw = (frm) => frm && frm.doctype === doctype && frm.doc.docstatus === 0 && onedesk.head.preview(frm);
	frappe.model.on(doctype, "*", (fieldname) => live.fields.includes(fieldname) && redraw(cur_frm));
	for (const [table, child] of Object.entries(live.tables)) {
		frappe.model.on(child, "*", () => redraw(cur_frm));
		frappe.ui.form.on(child, { [`${table}_remove`]: redraw });
	}
};

onedesk.head.sections = (doctype) => (frappe.boot.one_linked || {})[doctype] || [];

onedesk.head.drawn = (doctype) =>
	onedesk.head.sections(doctype).map((section) => [
		{ fieldtype: "Section Break", fieldname: `one_linked__${section.link_field}`, label: section.label, parent: doctype },
		...section.layout.map((df) => ({ ...df, read_only: 1, allow_on_submit: 1, parent: doctype })),
	]);

onedesk.head.place = (fields, placed_in) => {
	const at = Math.max(placed_in ? fields.findIndex((df) => df.fieldname === placed_in) : 0, 0);
	const next = fields.findIndex((df, i) => i > at && df.fieldtype === "Tab Break");
	return next < 0 ? fields.length : next;
};

onedesk.head.listened = new Set();
onedesk.head.listen = (doctype) => {
	if (onedesk.head.listened.has(doctype)) return;
	onedesk.head.listened.add(doctype);
	const events = {};
	for (const section of onedesk.head.sections(doctype)) events[section.link_field] = (frm) => onedesk.head.linked(frm);
	if (Object.keys(events).length) frappe.ui.form.on(doctype, events);
};

(() => {
	const saving = frappe.ui.form.save;
	frappe.ui.form.save = function (frm, ...rest) {
		onedesk.head.collect(frm);
		return saving.call(this, frm, ...rest);
	};
})();

onedesk.head.columns = (doctype) =>
	frappe.meta
		.get_docfields(doctype)
		.filter((df) => !frappe.model.no_value_type.includes(df.fieldtype))
		.map((df) => df.fieldname);

onedesk.head.rows = (rows, doctype, own = (row) => row.__one_name) => {
	const columns = onedesk.head.columns(doctype);
	return (rows || []).map((row) => {
		const out = own(row) ? { name: own(row) } : {};
		for (const column of columns) out[column] = row[column] ?? null;
		return out;
	});
};

onedesk.head.same = (a, b) => {
	const plain = (key, value) => (value === null || value === undefined ? "" : typeof value === "number" ? String(value) : value);
	return JSON.stringify(a, plain) === JSON.stringify(b, plain);
};

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

onedesk.head.heard = new Set();
onedesk.head.hear = async (doctype, name) => {
	const key = `${doctype}:${name}`;
	if (onedesk.head.heard.has(key)) return;
	onedesk.head.heard.add(key);
	if (!onedesk.head.listening) {
		onedesk.head.listening = true;
		frappe.realtime.on("doc_update", onedesk.head.updated);
	}
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
		__("{0} {1} was changed by someone else. Refresh to see the latest.", [__(one.doctype), one.title]),
	);
};

onedesk.head.warn = (frm, title) => {
	frm.layout.message.children(".one-record-changed").remove();
	const $block = $(`<div class="form-message one-record-changed"></div>`).append(
		onedesk.shell.changed(title, () => frm.reload_doc()),
	);
	frm.layout.message.removeClass("hidden").prepend($block);
};

frappe.ui.form.Form.prototype.show_conflict_message = function () {
	if (!this.doc.__needs_refresh) return;
	if (!this.doc.__unsaved) return this.debounced_reload_doc();
	onedesk.head.warn(this, __("This form has been modified after you have loaded it"));
};
