// A board's items are changed from Boards, on a phone or a tablet; QR Codes
// gives each item a code to put where it is, which opens its buttons there
// (one_display/boards.py).
frappe.ui.form.on("Display Board", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Open in Boards"), () => frappe.set_route("boards", { board: frm.doc.name }));
		frm.add_custom_button(__("QR Codes"), async () => {
			const codes = await frappe.xcall("onedesk.one_display.boards.codes", { board: frm.doc.name });
			const dialog = new frappe.ui.Dialog({ title: __("QR Codes"), size: "large", primary_action_label: __("Print"), primary_action: () => print(codes) });
			dialog.$body.html(
				`<div class="row">${codes.map((one) => `<div class="col-sm-4 text-center mb-4"><div>${one.svg}</div><div class="mt-2">${frappe.utils.escape_html(one.item)}</div></div>`).join("")}</div>`
			);
			dialog.show();
		});
	},
});

// the codes alone on a page, one per item, for printing and putting up
function print(codes) {
	const page = window.open("", "_blank");
	if (!page) return;
	page.document.write(
		`<html><head><title>${__("QR Codes")}</title><style>body{font-family:sans-serif}div.one{display:inline-block;width:30%;margin:1.5%;text-align:center;page-break-inside:avoid}svg{width:100%;height:auto}</style></head><body>${codes
			.map((one) => `<div class="one">${one.svg}<p>${frappe.utils.escape_html(one.item)}</p></div>`)
			.join("")}</body></html>`
	);
	page.document.close();
	page.focus();
	page.print();
}
