frappe.provide("onedesk.record_tabs");

onedesk.record_tabs.drawers = {};

onedesk.record_tabs.register = (name, drawer) => {
	onedesk.record_tabs.drawers[name] = drawer || {};
};

onedesk.record_tabs.TAB = (name) => `__one_${name}_tab`;
onedesk.record_tabs.FIELD = (name) => `__one_${name}`;

onedesk.record_tabs.declared = () => frappe.boot.one_record_tabs || [];

// Whether a declared tab belongs on this record's form at all, wherever it is
// drawn (a record tab, or the window's record panel).
onedesk.record_tabs.applies = (frm, name) => {
	const tab = onedesk.record_tabs.declared().find((one) => one.name === name);
	if (!tab || !onedesk.record_tabs.drawers[tab.name] || !frm || !frm.meta) return false;
	if (tab.doctypes && !tab.doctypes.includes(frm.doctype)) return false;
	return !(tab.leaves_out || []).includes(frm.doctype);
};

onedesk.record_tabs.on = (layout) => {
	const frm = layout.frm;
	const meta = frm && frm.meta;
	if (!meta || layout.is_child_table || layout.doctype !== frm.doctype || meta.istable || meta.issingle) return [];
	return onedesk.record_tabs.declared().filter((tab) => {
		const drawer = onedesk.record_tabs.drawers[tab.name];
		if (!onedesk.record_tabs.applies(frm, tab.name)) return false;
		return !drawer.wanted || drawer.wanted(frm);
	});
};

(() => {
	const Layout = frappe.ui.form.Layout;
	const fields_of = Layout.prototype.get_doctype_fields;
	Layout.prototype.get_doctype_fields = function () {
		const fields = fields_of.call(this);
		for (const tab of onedesk.record_tabs.on(this)) {
			fields.push(
				{ fieldtype: "Tab Break", fieldname: onedesk.record_tabs.TAB(tab.name), label: tab.label },
				{ fieldtype: "HTML", fieldname: onedesk.record_tabs.FIELD(tab.name) }
			);
		}
		return fields;
	};
})();

onedesk.record_tabs.tab = (frm, name) =>
	((frm.layout && frm.layout.tabs) || []).find((one) => one.df.fieldname === onedesk.record_tabs.TAB(name));

onedesk.record_tabs.count = (frm, name, count) => {
	if (onedesk.window.panel_count) onedesk.window.panel_count(frm, name, count);
	const tab = onedesk.record_tabs.tab(frm, name);
	if (!tab) return;
	const $link = tab.tab_link.find(".nav-link");
	$link.find(".one-files-count").remove();
	if (count) $link.append(`<span class="one-files-count">${cint(count)}</span>`);
};

frappe.ui.form.on("*", {
	refresh(frm) {
		const drawn = onedesk.record_tabs
			.declared()
			.map((declared) => ({ name: declared.name, tab: onedesk.record_tabs.tab(frm, declared.name) }))
			.filter((one) => one.tab);
		if (!drawn.length) return;
		for (const { tab } of drawn) tab.df.hidden = frm.is_new() ? 1 : 0;
		frm.layout.refresh_tabs();
		if (frm.is_new()) return;
		for (const { name, tab } of drawn) {
			const drawer = onedesk.record_tabs.drawers[name];
			const field = frm.fields_dict[onedesk.record_tabs.FIELD(name)];
			if (drawer.refresh) drawer.refresh(frm, field, tab);
			if (!drawer.open) continue;
			const $link = tab.tab_link.find(".nav-link");
			if (!$link.data("one-tab")) $link.data("one-tab", 1).on("click", () => drawer.open(frm, field, tab));
			if (tab.is_active() || (drawer.opened && drawer.opened(frm, field))) drawer.open(frm, field, tab);
		}
	},
});
