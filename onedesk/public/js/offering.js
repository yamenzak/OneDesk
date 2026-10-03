// A plan, a credit pack or an add-on, from the operator's side. Who has it,
// and what an edit here does to them, is its Record Head's sentence
// (one_admin/heads.py). The form shows only what its kind carries
// (`offering.py` CARRIES), and says what nought means for that kind.
frappe.ui.form.on("Offering", {
	refresh(frm) {
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		onedesk.offering.say(frm);
		if (frm.is_new()) return;
		// The connections count a plan's workspaces and signups; nobody is
		// "on" an add-on or a pack, so theirs would read nought.
		if (frm.doc.kind !== "Plan") frm.dashboard.links_area && frm.dashboard.links_area.hide();
		// An add-on's workspaces carry it in a table, which the connections
		// cannot count: this lists them.
		if (frm.doc.kind === "Add-on") {
			frm.add_custom_button(__("View Workspaces"), () =>
				frappe.xcall("onedesk.one_admin.operator.sold", { offering: frm.doc.name }).then((sold) =>
					frappe.set_route("List", "Tenant", { name: ["in", sold.workspaces.length ? sold.workspaces : [""]] }),
				),
			);
		}
		if (frappe.model.can_read("Item")) {
			// Its Item's code is `books.item_code`: ONE- and the key.
			const item = `ONE-${frm.doc.name}`.toUpperCase();
			frm.add_custom_button(__("View Item"), () =>
				frappe.db.exists("Item", item).then((there) =>
					there ? frappe.set_route("Form", "Item", item) : frappe.show_alert(__("No item yet")),
				),
			);
		}
	},
	kind(frm) {
		onedesk.offering.say(frm);
	},
	enabled(frm) {
		if (frm.doc.enabled || frm.is_new()) return;
		frappe.show_alert({
			message: __("Existing workspaces keep it. New signups can't pick it."),
			indicator: "blue",
		});
	},
});

frappe.provide("onedesk.offering");

// What nought means depends on the kind: on a plan it is unlimited, on an
// add-on it is simply not what the add-on adds.
onedesk.offering.say = (frm) => {
	const plan = frm.doc.kind === "Plan";
	const zero = plan ? __("Zero means unlimited.") : __("Set only what this add-on adds.");
	["storage_gb", "database_gb", "seats"].forEach((field) => frm.set_df_property(field, "description", zero));
};
