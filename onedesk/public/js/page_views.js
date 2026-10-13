// A page that gathers some record types into one screen (Lots, Quotes, Sent
// Out, Upkeep) is one more view of those records, beside frappe's own. The
// page's head carries frappe's view switcher, leading to their List and
// Report views and to the reports that belong with them, and frappe's
// switcher on those lists leads back to the page. One registry serves both
// ways (docs/PASSOVER.md, Everything follows frappe).
frappe.provide("onedesk");

// Per page: its name in the switcher, and in order the record types it
// gathers, each with its plain name and the page's tab that shows it, then
// the script reports that go with them.
onedesk.page_views = {
	lots: {
		label: () => __("Lots"),
		doctypes: [
			["Batch", () => __("Batches"), "batches"],
			["Serial No", () => __("Serial Numbers"), "serials"],
		],
		reports: [
			["Batch Item Expiry Status", () => __("Batch Expiry")],
			["Batch-Wise Balance History", () => __("Stock by Batch")],
		],
	},
	quotes: {
		label: () => __("Quotes"),
		doctypes: [
			["Request for Quotation", () => __("Requests for Quotation"), "asked"],
			["Supplier Quotation", () => __("Supplier Quotations"), "quotes"],
		],
		reports: [["Supplier Quotation Comparison", () => __("Quote Comparison")]],
	},
	"sent-out": {
		label: () => __("Sent Out"),
		doctypes: [
			["Subcontracting Order", () => __("Subcontracting Orders"), "out"],
			["Subcontracting Receipt", () => __("Subcontracting Receipts"), "done"],
		],
		reports: [["Subcontract Order Summary", () => __("Sent Out to Be Made")]],
	},
	upkeep: {
		label: () => __("Upkeep"),
		doctypes: [
			["Asset Maintenance Log", () => __("Maintenance Log"), "due"],
			["Asset Repair", () => __("Repairs"), "repairs"],
			["Asset Maintenance", () => __("Maintenance"), "plans"],
		],
		reports: [],
	},
};

// The page that gathers a record type, and the tab that shows it.
onedesk.page_views.page_of = (doctype) => {
	for (const [page, said] of Object.entries(onedesk.page_views)) {
		if (typeof said !== "object") continue;
		const found = said.doctypes.find(([one]) => one === doctype);
		if (found) return { page, label: said.label(), view: found[2] };
	}
	return null;
};

// The switcher on a page, as frappe draws it on a list (ListViewSelect): the
// page's own name selected, then List View and Report View, each naming the
// record types when the page gathers more than one.
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
			{ label: said.label(), icon: icons.Dashboard, selected: true },
			row("List", listed),
			row(
				"Report",
				reported,
				reports.map(([report, label]) => ({ label: label(), onclick: () => frappe.set_route("query-report", report) }))
			),
		].filter(Boolean);
	};
	// The head is drawn again whenever the page reports, so one switcher.
	page.custom_actions.add(page.custom_mobile_actions).children(".view-switcher").remove();
	const $wrapper = $('<div class="custom-btn-group view-switcher"></div>');
	const $trigger = frappe.ui.button({ css_class: "ellipsis" });
	frappe.ui.button.dress($trigger, { label: said.label(), icon: icons.Dashboard, icon_right: "chevrons-up-down" });
	$trigger.find(".es-button__label").addClass("hidden-xs custom-btn-group-label");
	$trigger.children("svg").last().addClass("hidden-xs");
	$wrapper.append($trigger);
	new frappe.ui.Dropdown({ trigger: $trigger, options });
	const parent = frappe.is_mobile() ? page.custom_mobile_actions : page.custom_actions;
	parent.removeClass("hide").append($wrapper);
};

// frappe's switcher on a record type's list leads back to the page that
// gathers it, as the first row.
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
