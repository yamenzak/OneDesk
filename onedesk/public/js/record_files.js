// Files on every record: a tab at the end of the form, holding OneCloud
// opened on the record's own room (@records/<doctype>/<name>) — the same
// explorer, the same verbs and the same permission, so what is attached here
// and what OneCloud shows under Records are one list.
//
// The tab is two fields added to the layout, not to the doctype: a Tab Break
// and an HTML field, appended where the form reads its fields
// (Layout.get_doctype_fields). Nothing is written to any doctype, erpnext's
// and hrms's included, and a form with no tabs of its own gets Frappe's own
// "Details" tab in front of it. The explorer is loaded the first time the tab
// is opened, so a form nobody opens Files on costs nothing.
frappe.provide("onedesk.record_files");

onedesk.record_files.TAB = "__one_files_tab";
onedesk.record_files.FIELD = "__one_files";

// Which forms carry it. A child row, a settings page and File itself have
// no room of their own.
onedesk.record_files.wanted = (layout) => {
	const frm = layout.frm;
	const meta = frm && frm.meta;
	if (!meta || layout.is_child_table || layout.doctype !== frm.doctype) return false;
	return !meta.istable && !meta.issingle && frm.doctype !== "File";
};

(() => {
	const Layout = frappe.ui.form.Layout;
	const fields_of = Layout.prototype.get_doctype_fields;
	Layout.prototype.get_doctype_fields = function () {
		const fields = fields_of.call(this);
		if (onedesk.record_files.wanted(this)) {
			fields.push(
				{ fieldtype: "Tab Break", fieldname: onedesk.record_files.TAB, label: __("Files") },
				{ fieldtype: "HTML", fieldname: onedesk.record_files.FIELD }
			);
		}
		return fields;
	};
})();

onedesk.record_files.room = (frm) => `@records/${frm.doctype}/${frm.doc.name}`;

onedesk.record_files.tab = (frm) =>
	((frm.layout && frm.layout.tabs) || []).find((one) => one.df.fieldname === onedesk.record_files.TAB);

// The count beside the tab's name, from what the form already knows and then
// from the explorer each time it lists the room.
onedesk.record_files.count = (frm, count) => {
	const tab = onedesk.record_files.tab(frm);
	if (!tab) return;
	const badge = count ? `<span class="one-files-count">${cint(count)}</span>` : "";
	const $link = tab.tab_link.find(".nav-link");
	$link.find(".one-files-count").remove();
	$link.append(badge);
	const $side = onedesk.record_files.side(frm);
	$side && $side.find(".one-files-count").remove();
	$side && $side.find(".explore-link").append(badge);
};

// The sidebar's Attachments list was the same files again, without preview,
// rename, sharing or versions, and with an uploader of its own. It becomes
// one row, "Files" and the count, which opens the tab.
onedesk.record_files.side = (frm) => {
	const $side = frm.attachments && frm.attachments.parent;
	if (!$side || !$side.length) return null;
	if (!$side.hasClass("one-files-side")) {
		$side.addClass("one-files-side");
		const $link = $side.find(".explore-link");
		$link.contents().filter((_, node) => node.nodeType === 3 && node.textContent.trim()).remove();
		$link.append(`<span class="one-files-label">${__("Files")}</span>`);
		$link.off("click").on("click", (e) => {
			e.preventDefault();
			const tab = onedesk.record_files.tab(frm);
			if (!tab) return;
			tab.set_active();
			onedesk.record_files.open(frm);
			frm.layout.wrapper[0].scrollIntoView({ block: "start", behavior: "smooth" });
		});
	}
	return $side;
};

// The explorer listed the room: the tab's count, and — when a file came or
// went through it — the form's own attachment list and timeline, which read
// docinfo and would otherwise not know until the form is reloaded.
onedesk.record_files.listed = (frm, count) => {
	onedesk.record_files.count(frm, count);
	const known = ((frm.get_docinfo() || {}).attachments || []).length;
	if (count !== known && frm.sidebar && frm.sidebar.reload_docinfo) frm.sidebar.reload_docinfo();
};

onedesk.record_files.open = (frm) => {
	const field = frm.fields_dict[onedesk.record_files.FIELD];
	if (!field || frm.is_new()) return;
	const room = onedesk.record_files.room(frm);
	if (field.onecloud) return field.onecloud.enter(room);
	if (field.loading) return;
	field.loading = frappe.require(["/assets/onedesk/css/onecloud.css", "/assets/onedesk/js/onecloud.js"]).then(() => {
		field.onecloud = new onedesk.OneCloud(null, {
			room,
			parent: field.$wrapper.empty().closest(".form-section").addClass("one-files-section").end(),
			listed: (count) => onedesk.record_files.listed(frm, count),
		});
	});
};

frappe.ui.form.on("*", {
	refresh(frm) {
		const tab = onedesk.record_files.tab(frm);
		if (!tab) return;
		// Nothing to hold files for until the record is saved.
		tab.df.hidden = frm.is_new() ? 1 : 0;
		// Frappe's own pass, so a form left with one tab shows no strip.
		frm.layout.refresh_tabs();
		if (frm.is_new()) return;
		onedesk.record_files.side(frm);
		onedesk.record_files.count(frm, ((frm.get_docinfo() || {}).attachments || []).length);
		const $link = tab.tab_link.find(".nav-link");
		if (!$link.data("one-files")) {
			$link.data("one-files", 1).on("click", () => onedesk.record_files.open(frm));
		}
		const field = frm.fields_dict[onedesk.record_files.FIELD];
		if (tab.is_active() || (field && field.onecloud)) onedesk.record_files.open(frm);
	},
});
