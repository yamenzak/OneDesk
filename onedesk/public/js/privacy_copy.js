// A copy of somebody's data (one/privacy_copy.py), reviewed by a workspace
// administrator before it goes: what is about the person always goes; what
// they wrote or touched may be withheld, kind by kind, with a reason they are
// told (GDPR article 15(4)). Decided here, never by editing the record.
frappe.ui.form.on("Personal Data Download Request", {
	refresh(frm) {
		// frappe's controller keeps user_name from the browser; the name comes from the user.
		const who = frappe.user.full_name(frm.doc.user) || frm.doc.user;
		const status = frm.doc.one_status || "Ready";
		frm.set_intro(
			{
				Waiting: __("{0} asked for a copy of their data. Send it within one month.", [who]),
				Gathering: __("Approved. The copy will be sent to {0} when it's ready.", [who]),
				Ready: __("Sent. {0} can download it from their profile.", [who]),
			}[status] || "",
			status === "Waiting" ? "blue" : "green"
		);
		if (status !== "Waiting" || !frappe.user.has_role("Workspace Administrator")) return;
		frm.page.set_primary_action(__("Review and Send"), () => onedesk.privacy_copy.review(frm));
	},
});

frappe.provide("onedesk.privacy_copy");

onedesk.privacy_copy.review = async (frm) => {
	const said = await frappe.xcall("onedesk.one.privacy_copy.review", { name: frm.doc.name });
	const counted = (one) => (one.count ? __("{0} ({1})", [one.label, one.count]) : __("{0} (none)", [one.label]));
	const fields = [
		{ fieldtype: "HTML", options: `<p>${__("Always included")}</p>` },
		...said.kinds.filter((one) => one.always).map((one) => ({ fieldtype: "Check", fieldname: one.key, label: counted(one), default: 1, read_only: 1 })),
		{ fieldtype: "Section Break" },
		{ fieldtype: "HTML", options: `<p>${__("Included unless unticked. Withhold only what is confidential to others or the company.")}</p>` },
		...said.kinds.filter((one) => !one.always).map((one) => ({ fieldtype: "Check", fieldname: one.key, label: counted(one), default: 1 })),
		{
			fieldtype: "Small Text",
			fieldname: "why",
			label: __("Reason for Withholding"),
			depends_on: `eval:${said.kinds
				.filter((one) => !one.always)
				.map((one) => `!doc.${one.key}`)
				.join(" || ")}`,
			mandatory_depends_on: `eval:${said.kinds
				.filter((one) => !one.always)
				.map((one) => `!doc.${one.key}`)
				.join(" || ")}`,
			description: __("Sent to {0}.", [frappe.utils.escape_html(said.person)]),
		},
	];
	const dialog = new frappe.ui.Dialog({
		title: __("Copy of Data for {0}", [said.person]),
		fields,
		primary_action_label: __("Send"),
		primary_action: async (values) => {
			const withheld = said.kinds.filter((one) => !one.always && !values[one.key]).map((one) => one.key);
			await frappe.xcall("onedesk.one.privacy_copy.send", { name: frm.doc.name, withheld, why: values.why || "" });
			dialog.hide();
			frappe.show_alert({ message: __("Preparing the copy for {0}.", [said.person]), indicator: "green" });
			frm.reload_doc();
		},
	});
	dialog.show();
};
