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
				Waiting: __("{0} asked for a copy of their data. Review it and send it within a month, as the law requires.", [who]),
				Gathering: __("Approved. The copy is being prepared and will be sent to {0}.", [who]),
				Ready: __("Sent. {0} downloads it from their profile.", [who]),
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
		{ fieldtype: "HTML", options: `<p>${__("Always given, because it is about {0}:", [frappe.utils.escape_html(said.person)])}</p>` },
		...said.kinds.filter((one) => one.always).map((one) => ({ fieldtype: "Check", fieldname: one.key, label: counted(one), default: 1, read_only: 1 })),
		{ fieldtype: "Section Break" },
		{ fieldtype: "HTML", options: `<p>${__("Given unless you untick it. Untick only what would show other people's or the company's confidential information, and say why.")}</p>` },
		...said.kinds.filter((one) => !one.always).map((one) => ({ fieldtype: "Check", fieldname: one.key, label: counted(one), default: 1 })),
		{
			fieldtype: "Small Text",
			fieldname: "why",
			label: __("Why Something Is Withheld"),
			depends_on: `eval:${said.kinds
				.filter((one) => !one.always)
				.map((one) => `!doc.${one.key}`)
				.join(" || ")}`,
			mandatory_depends_on: `eval:${said.kinds
				.filter((one) => !one.always)
				.map((one) => `!doc.${one.key}`)
				.join(" || ")}`,
			description: __("{0} is told this.", [frappe.utils.escape_html(said.person)]),
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
			frappe.show_alert({ message: __("Gathering the copy for {0}.", [said.person]), indicator: "green" });
			frm.reload_doc();
		},
	});
	dialog.show();
};
