frappe.provide("onedesk.record_activity");

onedesk.record_activity.tab = (frm) => onedesk.record_tabs.tab(frm, "activity");

onedesk.record_activity.count = (frm) =>
	onedesk.record_tabs.count(frm, "activity", ((frm.get_docinfo() || {}).comments || []).length);

(() => {
	const Footer = frappe.ui.form.Footer;
	const counted = Footer.prototype.refresh_comments_count;
	Footer.prototype.refresh_comments_count = function () {
		counted.call(this);
		onedesk.record_activity.count(this.frm);
	};
})();

onedesk.record_tabs.register("activity", {
	wanted: (frm) => !frm.meta.hide_toolbar && frappe.boot.desk_settings.timeline && !(onedesk.interface.panelled && onedesk.interface.panelled(frm)),
	refresh(frm, field, tab) {
		if (!field || !frm.footer) return;
		const footer = frm.footer.wrapper;
		const pane = tab.wrapper;
		if (footer && pane && !$.contains(pane[0], footer[0])) {
			field.$wrapper.closest(".form-section").addClass("one-activity-field");
			footer.appendTo(pane);
		}
		onedesk.record_activity.count(frm);
	},
});
