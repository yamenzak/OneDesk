// Activity on every record: comments, mail, changes, assignments and shares
// in a tab of their own, the last one, instead of under every tab. Under the
// Mail and Files tabs they repeated what those tabs show, and on a long form
// they were further down than anybody scrolled.
//
// The tab holds Frappe's own footer (frappe.ui.form.Footer): its comment box
// and timeline, moved into the tab rather than rebuilt, so everything they do
// still works. Frappe had the same tab sketched and left commented out in
// form.js. Like Files (record_files.js), the tab is added to the layout, not
// to any doctype.
frappe.provide("onedesk.record_activity");

onedesk.record_activity.TAB = "__one_activity_tab";
onedesk.record_activity.FIELD = "__one_activity";

(() => {
	const Layout = frappe.ui.form.Layout;
	const fields_of = Layout.prototype.get_doctype_fields;
	Layout.prototype.get_doctype_fields = function () {
		const fields = fields_of.call(this);
		const frm = this.frm;
		// Where Frappe draws a footer at all, and where Files is: every record.
		if (onedesk.record_files.wanted(this) && !frm.meta.hide_toolbar && frappe.boot.desk_settings.timeline) {
			fields.push(
				{ fieldtype: "Tab Break", fieldname: onedesk.record_activity.TAB, label: __("Activity") },
				{ fieldtype: "HTML", fieldname: onedesk.record_activity.FIELD }
			);
		}
		return fields;
	};
})();

onedesk.record_activity.tab = (frm) =>
	((frm.layout && frm.layout.tabs) || []).find((one) => one.df.fieldname === onedesk.record_activity.TAB);

// The comments beside the tab's name, as Files shows its files.
onedesk.record_activity.count = (frm) => {
	const tab = onedesk.record_activity.tab(frm);
	if (!tab) return;
	const count = ((frm.get_docinfo() || {}).comments || []).length;
	const $link = tab.tab_link.find(".nav-link");
	$link.find(".one-files-count").remove();
	if (count) $link.append(`<span class="one-files-count">${cint(count)}</span>`);
};

// A comment added or deleted: the count follows, as Frappe's own does.
(() => {
	const Footer = frappe.ui.form.Footer;
	const counted = Footer.prototype.refresh_comments_count;
	Footer.prototype.refresh_comments_count = function () {
		counted.call(this);
		onedesk.record_activity.count(this.frm);
	};
})();

frappe.ui.form.on("*", {
	refresh(frm) {
		const tab = onedesk.record_activity.tab(frm);
		const field = frm.fields_dict[onedesk.record_activity.FIELD];
		if (!tab || !field || !frm.footer) return;
		// A new record has nothing to show yet; Frappe hides its footer too.
		tab.df.hidden = frm.is_new() ? 1 : 0;
		frm.layout.refresh_tabs();
		// Into the tab's pane itself, not the HTML field: inside a control,
		// Frappe's `.frappe-control .action-btn` would pin the timeline's
		// buttons as if they were a link field's. The field only makes the tab.
		const footer = frm.footer.wrapper;
		const pane = tab.wrapper;
		if (footer && pane && !$.contains(pane[0], footer[0])) {
			// The field's section stays, emptied of its padding: frappe shows a
			// tab only while it has a visible section, and hides this one on its
			// next refresh of the tabs if the section is hidden.
			field.$wrapper.closest(".form-section").addClass("one-activity-field");
			footer.appendTo(pane);
		}
		onedesk.record_activity.count(frm);
	},
});
