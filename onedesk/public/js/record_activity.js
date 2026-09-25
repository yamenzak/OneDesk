// Activity on every record: comments, mail, changes, assignments and shares
// in a tab of their own, the last one, instead of under every tab. Under the
// Mail and Files tabs they repeated what those tabs show, and on a long form
// they were further down than anybody scrolled.
//
// The tab holds Frappe's own footer (frappe.ui.form.Footer): its comment box
// and timeline, moved into the tab rather than rebuilt, so everything they do
// still works. Frappe had the same tab sketched and left commented out in
// form.js. Declared in one/tabs.py and drawn here, as every record tab is
// (record_tabs.js).
frappe.provide("onedesk.record_activity");

onedesk.record_activity.tab = (frm) => onedesk.record_tabs.tab(frm, "activity");

// The comments beside the tab's name, as Files shows its files.
onedesk.record_activity.count = (frm) =>
	onedesk.record_tabs.count(frm, "activity", ((frm.get_docinfo() || {}).comments || []).length);

// A comment added or deleted: the count follows, as Frappe's own does.
(() => {
	const Footer = frappe.ui.form.Footer;
	const counted = Footer.prototype.refresh_comments_count;
	Footer.prototype.refresh_comments_count = function () {
		counted.call(this);
		onedesk.record_activity.count(this.frm);
	};
})();

onedesk.record_tabs.register("activity", {
	// Where Frappe draws a footer at all.
	wanted: (frm) => !frm.meta.hide_toolbar && frappe.boot.desk_settings.timeline,
	refresh(frm, field, tab) {
		if (!field || !frm.footer) return;
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
