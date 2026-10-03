// A custom collection, from the administrator's side. OneAI made it and
// changes it, so there is nothing to type and no Save. Its fields stay on the
// doctype for the list and OneAI; on the form they are read as a page: the
// collection's own fields, where its records are, and what was asked.
const DRAWN = ["section_details", "record_doctype", "app", "description", "asked", "asked_by"];

frappe.ui.form.on("Record Type", {
	refresh(frm) {
		frm.disable_save();
		frm.sidebar?.sidebar
			.find(".form-assignments, .form-attachments, .form-tags, .form-shared")
			.addClass("hidden");
		frm.toggle_display(DRAWN, false);
		frm.events.draw(frm);
	},

	async draw(frm) {
		const field = frm.fields_dict.summary;
		if (!field || frm.is_new()) return;
		const esc = frappe.utils.escape_html;
		const shell = onedesk.shell;
		const doc = frm.doc;
		const name = __(doc.record_doctype);
		const records = `/desk/${frappe.router.slug(doc.record_doctype)}`;

		const by = [
			doc.asked_by ? esc(frappe.user.full_name(doc.asked_by)) : "",
			frappe.datetime.comment_when(doc.creation),
		]
			.filter(Boolean)
			.join(" · ");
		field.$wrapper.html(`<div class="one-collection">
			${shell.section(
				__("Where It Is"),
				shell.row({
					title: esc(doc.app === "One" ? __("One › Your Records") : __("{0} › Your Records", [__(doc.app)])),
					actions: `<a class="btn btn-default btn-sm" href="${records}">${esc(__("Open {0}", [name]))}</a>`,
				}),
			)}
			<div class="one-shell-section" data-part="fields"></div>
			${doc.asked ? shell.section(__("Asked"), `<div class="one-extension-asked"><div class="one-extension-text">${esc(doc.asked)}</div><span class="one-shell-quiet">${by}</span></div>`) : ""}
		</div>`);

		// The collection's own fields, as frappe keeps them.
		await frappe.model.with_doctype(doc.record_doctype);
		const meta = frappe.get_meta(doc.record_doctype);
		const fields = (meta ? meta.fields : []).filter(
			(df) => !["Section Break", "Column Break", "Tab Break"].includes(df.fieldtype) && !df.hidden,
		);
		const yes = (on) => (on ? frappe.ui.badge.html({ label: __("Yes"), theme: "gray" }) : "");
		shell.table(field.$wrapper.find('[data-part="fields"]'), {
			title: __("Fields"),
			rows: fields,
			icon: "text-cursor-input",
			empty: __("No fields"),
			actions: onedesk.oneai.button(__("Add Field"), __("I want to add a field to {0}.", [name])),
			columns: [
				{ label: __("Field"), render: (df) => esc(__(df.label || df.fieldname)) },
				{ label: __("Type"), render: (df) => esc(__(df.fieldtype)) + (df.fieldtype === "Link" ? ` <span class="one-shell-quiet">${esc(__(df.options))}</span>` : "") },
				{ label: __("Required"), render: (df) => yes(df.reqd) },
				{ label: __("In List View"), render: (df) => yes(df.in_list_view) },
			],
		});
	},
});
