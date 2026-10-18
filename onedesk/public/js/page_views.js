frappe.provide("onedesk");

onedesk.page_views = {
	lots: {
		label: () => __("Batch and Serial No"),
		doctypes: [
			["Batch", () => __("Batch"), "batches"],
			["Serial No", () => __("Serial No"), "serials"],
		],
		reports: [
			["Batch Item Expiry Status", () => __("Batch Item Expiry Status")],
			["Batch-Wise Balance History", () => __("Batch-Wise Balance History")],
		],
	},
	quotes: {
		label: () => __("Request for Quotation"),
		doctypes: [
			["Request for Quotation", () => __("Request for Quotation"), "asked"],
			["Supplier Quotation", () => __("Supplier Quotation"), "quotes"],
		],
		reports: [["Supplier Quotation Comparison", () => __("Supplier Quotation Comparison")]],
	},
	"sent-out": {
		label: () => __("Subcontracting Order"),
		doctypes: [
			["Subcontracting Order", () => __("Subcontracting Order"), "out"],
			["Subcontracting Receipt", () => __("Subcontracting Receipt"), "done"],
		],
		reports: [["Subcontract Order Summary", () => __("Subcontract Order Summary")]],
	},
	upkeep: {
		label: () => __("Asset Maintenance"),
		doctypes: [
			["Asset Maintenance Log", () => __("Asset Maintenance Log"), "due"],
			["Asset Repair", () => __("Asset Repair"), "repairs"],
			["Asset Maintenance", () => __("Asset Maintenance"), "plans"],
		],
		reports: [],
	},
};

onedesk.page_views.page_of = (doctype) => {
	for (const [page, said] of Object.entries(onedesk.page_views)) {
		if (typeof said !== "object") continue;
		const found = said.doctypes.find(([one]) => one === doctype);
		if (found) return { page, label: said.label(), view: found[2] };
	}
	return null;
};

onedesk.page_views.switcher = (page, name) => {
	const said = onedesk.page_views[name];
	if (!said) return;
	const icons = frappe.views.view_icon_map;
	const labels = frappe.views.get_view_label_map();
	const slug = (doctype) => frappe.router.slug(doctype);
	const options = () => {
		const listed = said.doctypes.filter(([doctype]) => frappe.model.can_read(doctype));
		const reported = said.doctypes.filter(([doctype]) => frappe.model.can_get_report(doctype));
		const reports = said.reports.filter(([report]) => frappe.boot.user.all_reports?.[report]);
		const row = (view, rows, extra = []) => {
			if (!rows.length && !extra.length) return null;
			const go = (doctype) => frappe.set_route(view === "List" ? `/desk/${slug(doctype)}` : `/desk/${slug(doctype)}/view/report`);
			const item = { label: labels[view], icon: icons[view] };
			if (rows.length === 1 && !extra.length) item.onclick = () => go(rows[0][0]);
			else {
				item.submenu = rows.map(([doctype, label]) => ({ label: label(), onclick: () => go(doctype) }));
				if (extra.length) item.submenu.push({ group: __("Reports"), options: extra });
			}
			return item;
		};
		return [
			{ label: __("Overview"), icon: icons.Dashboard, selected: true },
			row("List", listed),
			row(
				"Report",
				reported,
				reports.map(([report, label]) => ({ label: label(), onclick: () => frappe.set_route("query-report", report) }))
			),
		].filter(Boolean);
	};
	page.custom_actions.add(page.custom_mobile_actions).children(".view-switcher").remove();
	const $wrapper = $('<div class="custom-btn-group view-switcher"></div>');
	const $trigger = frappe.ui.button({ css_class: "ellipsis" });
	frappe.ui.button.dress($trigger, { label: __("Overview"), icon: icons.Dashboard, icon_right: "chevrons-up-down" });
	$trigger.find(".es-button__label").addClass("hidden-xs custom-btn-group-label");
	$trigger.children("svg").last().addClass("hidden-xs");
	$wrapper.append($trigger);
	new frappe.ui.Dropdown({ trigger: $trigger, options });
	const parent = frappe.is_mobile() ? page.custom_mobile_actions : page.custom_actions;
	parent.removeClass("hide").append($wrapper);
};

(() => {
	const Select = frappe.views.ListViewSelect;
	if (!Select || Select.prototype.one_page_views) return;
	Select.prototype.one_page_views = true;
	const options = Select.prototype.get_view_options;
	Select.prototype.get_view_options = function () {
		const rows = options.call(this);
		const gathered = onedesk.page_views.page_of(this.doctype);
		if (!gathered || !frappe.boot.page_info?.[gathered.page]) return rows;
		return [
			{
				label: gathered.label,
				icon: frappe.views.view_icon_map.Dashboard,
				onclick: () => frappe.set_route(`/desk/${gathered.page}?view=${gathered.view}`),
			},
			...rows,
		];
	};
})();
