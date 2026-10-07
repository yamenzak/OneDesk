// Contracts: whether each is signed and when it ends, and the project it is
// for by name (one_project/agreement.py). ERPNext's list read "Draft" for an
// unsigned contract, since it never asked a draft for its status.
const ONE_FOR = {};
const SIGNED = { Unsigned: "orange", Active: "green", Inactive: "gray" };

frappe.listview_settings["Contract"] = Object.assign(frappe.listview_settings["Contract"] || {}, {
	hide_name_column: true,
	has_indicator_for_draft: true,
	get_indicator(doc) {
		if (doc.docstatus === 2) return [__("Cancelled"), "red", "docstatus,=,2"];
		return [__(doc.status), SIGNED[doc.status] || "gray", `status,=,${doc.status}`];
	},
	formatters: {
		document_name(value, df, doc) {
			return (doc.document_type === "Project" && ONE_FOR[value]) || value;
		},
	},
	refresh(listview) {
		const missing = [
			...new Set(listview.data.filter((doc) => doc.document_type === "Project").map((doc) => doc.document_name)),
		].filter((name) => name && !(name in ONE_FOR));
		if (!missing.length) return;
		frappe.db
			.get_list("Project", { filters: { name: ["in", missing] }, fields: ["name", "project_name"], limit: missing.length })
			.then((rows) => {
				for (const name of missing) ONE_FOR[name] = name;
				for (const row of rows) ONE_FOR[row.name] = row.project_name || row.name;
				listview.render();
			});
	},
});
(frappe.listview_settings["Contract"].add_fields = frappe.listview_settings["Contract"].add_fields || []).push(
	"status",
	"document_type"
);
