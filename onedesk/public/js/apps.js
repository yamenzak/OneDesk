frappe.provide("onedesk.apps");

onedesk.apps.hidden = () => new Set(frappe.boot.one_hidden?.doctypes || []);
onedesk.apps.ai = () => frappe.boot.one_hidden?.ai !== false;
onedesk.apps.intake = () => frappe.boot.one_hidden?.intake !== false;
onedesk.apps.editing = (kind) => frappe.boot.one_editors?.[kind] !== false;

onedesk.apps.button = ($dock) => {
	const $user = $dock.find(".dock-user");
	if (!$user.length || $dock.find(".one-apps-button").length) return;
	const $button = $(
		`<div class="one-apps"><button class="dock-item one-apps-button" aria-label="${__("Apps")}">${frappe.utils.icon(
			"layout-grid",
			"md"
		)}</button></div>`
	)
		.insertBefore($user)
		.find("button");
	$button.on("click", (event) => {
		event.stopPropagation();
		onedesk.rail.launcher();
	});
	onedesk.interface.tips.name($button[0], __("Apps"));
};

if (frappe.search?.AwesomeBar) {
	const build = frappe.search.AwesomeBar.prototype.build_options;
	frappe.search.AwesomeBar.prototype.build_options = function (txt) {
		const hidden = onedesk.apps.hidden();
		const found = build.call(this, txt);
		if (!hidden.size) return found;
		return found.filter((one) => !(one.route && hidden.has(one.route[1])));
	};
}

frappe.ui.form.on("*", {
	refresh(frm) {
		const hidden = onedesk.apps.hidden();
		if (!hidden.size) return;
		for (const df of frm.meta.fields) {
			if (df.fieldtype !== "Link" || !hidden.has(df.options) || df.hidden) continue;
			frm.toggle_display(df.fieldname, !!frm.doc[df.fieldname]);
		}
	},
});

if (frappe.ui.Dock) {
	const make = frappe.ui.Dock.prototype.make;
	frappe.ui.Dock.prototype.make = function () {
		make.call(this);
		onedesk.apps.button(this.$dock);
	};
}

$(document).on("app_ready", () => {
	onedesk.apps.button($("#desk-dock"));
	frappe.realtime.on("one_apps", () =>
		frappe.show_alert({ message: __("The workspace's apps changed. Reload to see them."), indicator: "blue" }, 10)
	);
});
