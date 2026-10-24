frappe.provide("onedesk.intake");

onedesk.intake.MARK = "/assets/onedesk/images/oneai.svg";

// A record OneAI made says so above its form until a person has checked it
// (one_intake/mark.py). What OneAI read from a file or a message is drawn by
// the islands (frontend/src/intake).
$(document).on("form-refresh", (event, frm) => {
	const held = (frm.doc.__onload || {}).one_intake_mark;
	if (!held) return;
	const esc = frappe.utils.escape_html;
	const doc = held.document || {};
	const from = doc.route ? `<a href="${esc(doc.route)}">${esc(doc.label || "")}</a>` : esc(doc.label || "");
	frm.set_intro(
		`<div class="oi-banner"><img src="${onedesk.intake.MARK}" alt="">
		<span>${from ? __("Made by OneAI from {0}. Not checked yet.", [from]) : __("Made by OneAI. Not checked yet.")}</span>
		<span class="oi-buttons">${frappe.ui.button.html({ label: __("Mark as Checked"), size: "xs", attrs: { "data-looks-right": true } })}
		${held.action ? frappe.ui.button.html({ label: __("Undo"), size: "xs", attrs: { "data-undo-one": true } }) : ""}</span></div>`,
		"blue"
	);
	const $banner = frm.$intro_message || $();
	$banner.find("[data-looks-right]").on("click", async () => {
		await frappe.xcall("onedesk.one_intake.mark.looks_right", { doctype: frm.doctype, name: frm.docname });
		delete frm.doc.__onload.one_intake_mark;
		frm.set_intro();
		frappe.show_alert({ message: __("Marked as checked"), indicator: "green" });
	});
	$banner.find("[data-undo-one]").on("click", () => {
		frappe.confirm(__("Undo what OneAI did here?"), async () => {
			const said = await frappe.xcall("onedesk.one_intake.act.undo_one", { action: held.action });
			if (said.why) {
				frappe.msgprint(said.why);
				return;
			}
			frappe.show_alert({ message: __("Undone"), indicator: "green" });
			frappe.set_route("List", frm.doctype);
		});
	});
});
