// A custom domain on a workspace, from the operator's side.
//
// Every field is Frappe Cloud's answer written down: the workspace asked for the
// name, Frappe Cloud points it and issues the certificate, and this record is a
// copy of where that got to. So the screen is read-only and carries one verb,
// which is to ask again.
frappe.ui.form.on("Tenant Domain", {
	refresh(frm) {
		if (frm.is_new()) return;
		onedesk.domain.draw(frm);

		frm.add_custom_button(__("Refresh"), () =>
			frappe
				.xcall("onedesk.one_admin.operator.refresh_domain", { domain: frm.doc.name })
				.then(() => frm.reload_doc())
				.catch(() => frm.reload_doc()),
		).addClass("btn-primary");
	},
});

frappe.provide("onedesk.domain");

onedesk.domain.SAYS = {
	Pending: ["orange", __("Waiting")],
	"In Progress": ["blue", __("Being set up")],
	Active: ["green", __("Active")],
	Broken: ["red", __("Not working")],
	Gone: ["grey", __("Removed")],
};

onedesk.domain.draw = (frm) => {
	const [colour, word] = onedesk.domain.SAYS[frm.doc.status] || ["grey", frm.doc.status];
	frm.page.set_indicator(word, colour);

	frm.dashboard.clear_headline();
	const said = onedesk.domain.headline(frm.doc);
	if (said) frm.dashboard.set_headline(said[1], said[0]);
};

// What a reader opens this screen to find out is why a name is not working yet,
// and there are only three answers: nobody has asked Frappe Cloud yet, it is
// working on it, or the customer's DNS does not point here.
onedesk.domain.headline = (doc) => {
	if (doc.status === "Broken") {
		return [
			"red",
			__("{0} does not point to this workspace. The customer has to change their DNS.", [
				doc.domain,
			]),
		];
	}
	if (doc.status === "Gone") {
		return ["grey", __("Frappe Cloud no longer has this domain.")];
	}
	if (doc.status === "In Progress") {
		return ["blue", __("Frappe Cloud is issuing the certificate. This takes a few minutes.")];
	}
	if (doc.status === "Pending") {
		return ["orange", __("Asked for, and Frappe Cloud has not answered yet.")];
	}
	return null;
};
