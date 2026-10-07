// Files on every record: a tab at the end of the form, holding OneCloud
// opened on the record's own room (@records/<doctype>/<name>) — the same
// explorer, the same verbs and the same permission, so what is attached here
// and what OneCloud shows under Records are one list.
//
// Declared in one_storage/namespace.py and drawn here, as every record tab
// is (record_tabs.js). The explorer is loaded the first time the tab is
// opened, so a form nobody opens Files on costs nothing.
frappe.provide("onedesk.record_files");

onedesk.record_files.room = (frm) => `@records/${frm.doctype}/${frm.doc.name}`;

onedesk.record_files.tab = (frm) => onedesk.record_tabs.tab(frm, "files");

// The count beside the tab's name, from what the form already knows and then
// from the explorer each time it lists the room.
onedesk.record_files.count = (frm, count) => {
	onedesk.record_tabs.count(frm, "files", count);
	onedesk.record_files.badge(onedesk.record_files.side(frm), count);
};

// The count beside the sidebar's Files row.
onedesk.record_files.badge = ($side, count) => {
	if (!$side) return;
	$side.find(".one-files-count").remove();
	if (count) $side.find(".explore-link").append(`<span class="one-files-count">${cint(count)}</span>`);
};

// The sidebar's Attachments list was the same files again, without preview,
// rename, sharing or versions, and with an uploader of its own. It becomes
// one row, "Files" and the count, which opens the record's files: the form's
// Files tab, or on a record's own page (onedesk.record.sidebar) the page's
// Files view or OneCloud on the record's room (`open`).
onedesk.record_files.side = (frm, open = () => onedesk.record_files.show(frm)) => {
	const $side = frm.attachments && frm.attachments.parent;
	if (!$side || !$side.length) return null;
	if (!$side.hasClass("one-files-side")) {
		$side.addClass("one-files-side");
		const $link = $side.find(".explore-link");
		$link.contents().filter((_, node) => node.nodeType === 3 && node.textContent.trim()).remove();
		$link.append(`<span class="one-files-label">${__("Files")}</span>`);
		$link.off("click").on("click", (e) => {
			e.preventDefault();
			open();
		});
	}
	return $side;
};

// The form's Files tab, opened and scrolled to.
onedesk.record_files.show = (frm) => {
	const tab = onedesk.record_files.tab(frm);
	if (!tab) return;
	tab.set_active();
	onedesk.record_files.open(frm);
	frm.layout.wrapper[0].scrollIntoView({ block: "start", behavior: "smooth" });
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
	const field = frm.fields_dict[onedesk.record_tabs.FIELD("files")];
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

onedesk.record_tabs.register("files", {
	refresh(frm) {
		onedesk.record_files.side(frm);
		onedesk.record_files.count(frm, ((frm.get_docinfo() || {}).attachments || []).length);
	},
	open: (frm) => onedesk.record_files.open(frm),
	opened: (frm, field) => Boolean(field && field.onecloud),
});
