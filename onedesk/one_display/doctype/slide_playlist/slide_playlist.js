// A slide playlist plays presentations from OneCloud and web pages. A row
// picks a presentation its maker may open; New Presentation makes one on
// this playlist and opens it in OneSlide; Open Presentation goes back to one.
frappe.ui.form.on("Slide Playlist", {
	setup(frm) {
		frm.set_query("presentation", "slides", () => ({ query: "onedesk.one_slide.api.search" }));
	},
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("New Presentation"), () =>
			frappe.prompt(
				[{ fieldname: "title", fieldtype: "Data", label: __("Title"), reqd: 1 }],
				async ({ title }) => {
					const made = await frappe.xcall("onedesk.one_slide.api.make", { parent: `@records/Slide Playlist/${frm.doc.name}`, title });
					frm.add_child("slides", { kind: "Presentation", presentation: made.id, title });
					await frm.save();
					frappe.set_route("presentation", made.presentation);
				},
				__("New Presentation"),
				__("Make")
			)
		);
		frm.change_custom_button_type(__("New Presentation"), null, "primary");
		for (const row of frm.doc.slides || []) {
			if (row.kind !== "Presentation" || !row.presentation) continue;
			frm.add_custom_button(
				row.title || row.presentation,
				async () => {
					const url = await frappe.db.get_value("File", row.presentation, "file_url");
					if (url?.message?.file_url) window.location.href = url.message.file_url;
				},
				__("Open Presentation")
			);
		}
	},
});
