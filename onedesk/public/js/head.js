// A record's head: the pill, the sentence, the band of numbers and the verbs
// above its fields, drawn from what the server worked out as the reader
// (one/head.py, `__onload.one_head`). One renderer for every doctype with a
// Record Head; nothing here knows any of them. docs/SHELL.md, decision 4.
frappe.provide("onedesk.head");

frappe.ui.form.on("*", {
	setup(frm) {
		// ERPNext's own refresh, which runs after ours, makes Create the primary
		// group. While a primary verb is on the page it is the one dark button.
		const primary = frm.page.set_inner_btn_group_as_primary.bind(frm.page);
		frm.page.set_inner_btn_group_as_primary = (label) =>
			frm.one_primary_verb && frm.custom_buttons[frm.one_primary_verb] ? null : primary(label);
	},
	refresh(frm) {
		onedesk.head.draw(frm);
	},
});

onedesk.head.draw = (frm) => {
	frm.one_primary_verb = null;
	const head = !frm.is_new() && frm.doc.__onload && frm.doc.__onload.one_head;
	// A form without a head is left as its own script drew it.
	if (!head && !frm.one_headed) return;
	frm.one_headed = !!head;
	// Only what this drew before goes: the message area is shared.
	frm.layout.message.children(".form-message:has(.one-head-sentence, .one-band)").remove();
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
