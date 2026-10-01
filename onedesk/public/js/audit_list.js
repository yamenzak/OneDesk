// The Audit Log (one/audit.py): frappe's own lists of changes, sign-ins and
// exports, headed as One's sidebar names them, each row said as a sentence:
// who did what to which record, as Activity Log already says a sign-in.
(() => {
	const who = (user) => frappe.user.full_name(user) || user;
	const headed = (title) => (list) => list.page.set_title(title);
	// The record a row is about, opened from the row's own button.
	const opens = (doctype, name) => ({
		show: (doc) => doc[doctype] && doc[name],
		get_label: () => __("Open"),
		get_description: (doc) => __("Open {0}", [doc[name]]),
		action: (doc) => frappe.set_route("Form", doc[doctype], doc[name]),
	});

	frappe.listview_settings["Version"] = {
		...frappe.listview_settings["Version"],
		hide_name_column: true,
		add_fields: ["owner", "ref_doctype", "docname"],
		formatters: {
			docname: (value, df, doc) => __("{0} changed {1}", [who(doc.owner), value]),
			ref_doctype: (value) => __(value),
		},
		button: opens("ref_doctype", "docname"),
		onload: headed(__("Changes")),
	};

	frappe.listview_settings["Activity Log"] = {
		...frappe.listview_settings["Activity Log"],
		hide_name_column: true,
		onload: headed(__("Sign-ins")),
	};

	frappe.listview_settings["Access Log"] = {
		...frappe.listview_settings["Access Log"],
		hide_name_column: true,
		add_fields: ["user", "export_from", "reference_document", "file_type", "report_name"],
		formatters: {
			name: (value, df, doc) =>
				doc.file_type === "PDF"
					? __("{0} printed {1}", [who(doc.user), doc.reference_document || __(doc.export_from)])
					: __("{0} exported {1}", [who(doc.user), doc.report_name || __(doc.export_from)]),
			export_from: (value) => __(value),
		},
		button: opens("export_from", "reference_document"),
		onload: headed(__("Exports and Prints")),
	};
})();
