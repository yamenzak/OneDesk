// What's New: a module's versions, newest first, with the ones the reader
// has not seen marked New (one/versions.py). Written in English only, for
// the people using the module, so its words are shown as written.
frappe.provide("onedesk.whats_new");

onedesk.whats_new.KINDS = () => ({ major: __("Major"), minor: __("Update"), fix: __("Fix") });

onedesk.whats_new.open = async (module) => {
	const said = await frappe.xcall("onedesk.one.versions.whats_new", { module });
	const esc = frappe.utils.escape_html;
	const kinds = onedesk.whats_new.KINDS();
	const dialog = new frappe.ui.Dialog({
		title: __("What's New in {0}", [module]),
		size: "large",
		fields: [{ fieldname: "versions", fieldtype: "HTML" }],
	});
	const $list = $(`<div class="one-whats-new"></div>`);
	for (const one of said.versions) {
		const badges = [
			one.new ? frappe.ui.badge.html({ label: __("New"), theme: "blue" }) : "",
			frappe.ui.badge.html({ label: kinds[one.kind] || one.kind, theme: "gray" }),
		].join(" ");
		$(`<article class="one-whats-new-entry"></article>`)
			.append(
				`<header class="one-whats-new-head">
					<span class="one-whats-new-title">${esc(one.title)}</span>
					<span class="one-whats-new-badges">${badges}</span>
				</header>
				<div class="one-whats-new-when">${esc(module)} ${esc(one.version)} · ${esc(frappe.datetime.str_to_user(one.date))}</div>`
			)
			.append($(`<div class="one-whats-new-body"></div>`).html(one.html))
			.appendTo($list);
	}
	dialog.fields_dict.versions.$wrapper.empty().append($list);
	dialog.show();
	const ours = frappe.boot.one_versions && frappe.boot.one_versions[module];
	if (ours) ours.unseen = 0;
	$(document).trigger("one-version-seen", [module]);
	return dialog;
};
