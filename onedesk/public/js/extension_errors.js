// An extension's Errors tab (one_studio/mend.py): what this version of it ran
// into, at most two weeks back: when, on which record, and what went wrong in
// one line. Never its code, which nobody on the workspace reads: Fix With
// OneAI, at the top of the extension, has OneAI read the code and these errors
// and write it again.
onedesk.record_tabs.register("errors", {
	async refresh(frm, field) {
		if (!field || frm.is_new()) return;
		const rows = await frappe.xcall("onedesk.one_studio.mend.listed", { extension: frm.doc.name });
		onedesk.record_tabs.count(frm, "errors", rows.length);
		const esc = frappe.utils.escape_html;
		field.$wrapper.empty();
		onedesk.shell.table(field.$wrapper, {
			note: __("Errors from the last two weeks, since the latest version. The record or form kept working."),
			rows,
			icon: "circle-check",
			empty: __("It has run into no errors since OneAI last wrote it."),
			columns: [
				{ label: __("When"), render: (one) => esc(frappe.datetime.str_to_user(one.on)) },
				{
					label: __("Record"),
					render: (one) =>
						one.record_name
							? `<a href="/desk/${frappe.router.slug(one.record_doctype)}/${encodeURIComponent(one.record_name)}">${esc(__(one.record_doctype))} ${esc(one.record_name)}</a>`
							: esc(__(one.record_doctype || "")),
				},
				{ label: __("What Went Wrong"), render: (one) => esc(one.what || "") },
			],
		});
	},
});
