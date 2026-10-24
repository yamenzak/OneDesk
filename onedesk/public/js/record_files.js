frappe.provide("onedesk.record_files");

onedesk.record_files.room = (frm) => `@records/${frm.doctype}/${frm.doc.name}`;

onedesk.record_files.tab = (frm) => onedesk.record_tabs.tab(frm, "files");

onedesk.record_files.count = (frm, count) => {
	onedesk.record_tabs.count(frm, "files", count);
	onedesk.record_files.badge(onedesk.record_files.side(frm), count);
};

onedesk.record_files.badge = ($side, count) => {
	if (!$side) return;
	$side.find(".one-files-count").remove();
	if (count) $side.find(".explore-link").append(`<span class="one-files-count">${cint(count)}</span>`);
};

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

onedesk.record_files.show = (frm) => {
	const tab = onedesk.record_files.tab(frm);
	if (!tab) return;
	tab.set_active();
	onedesk.record_files.open(frm);
	frm.layout.wrapper[0].scrollIntoView({ block: "start", behavior: "smooth" });
};

onedesk.record_files.listed = (frm, count) => {
	onedesk.record_files.count(frm, count);
	const known = ((frm.get_docinfo() || {}).attachments || []).length;
	if (count !== known && frm.sidebar && frm.sidebar.reload_docinfo) frm.sidebar.reload_docinfo();
};

// The record's folder over the record, in a dialog: closing it leaves the
// record as it was. Where the record panel is, this is how its files open.
onedesk.record_files.dialog = (frm) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Files of {0}", [frm.get_title() || frm.doc.name]),
		size: "extra-large",
		fields: [{ fieldtype: "HTML", fieldname: "files" }],
	});
	dialog.$wrapper.addClass("one-files-dialog");
	dialog.show();
	onedesk.mount_cloud(dialog.fields_dict.files.$wrapper, {
		room: onedesk.record_files.room(frm),
		onListed: (count) => onedesk.record_files.listed(frm, count),
	});
	return dialog;
};

onedesk.record_files.open = (frm) => {
	const field = frm.fields_dict[onedesk.record_tabs.FIELD("files")];
	if (!field || frm.is_new()) return;
	const room = onedesk.record_files.room(frm);
	if (field.onecloud) return field.onecloud.update({ room });
	if (field.loading) return;
	const $host = field.$wrapper.empty().closest(".form-section").addClass("one-files-section").end();
	field.loading = onedesk.mount_cloud($host, { room, onListed: (count) => onedesk.record_files.listed(frm, count) }).then((handle) => (field.onecloud = handle));
};

onedesk.record_tabs.register("files", {
	refresh(frm) {
		onedesk.record_files.side(frm);
		onedesk.record_files.count(frm, ((frm.get_docinfo() || {}).attachments || []).length);
	},
	open: (frm) => onedesk.record_files.open(frm),
	wanted: (frm) => !(onedesk.window.panelled && onedesk.window.panelled(frm)),
	opened: (frm, field) => Boolean(field && field.onecloud),
});
