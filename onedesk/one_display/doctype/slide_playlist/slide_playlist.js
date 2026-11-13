// A slide playlist plays presentations from OneCloud and web pages. A row
// picks a presentation its maker may open; New Presentation makes one on
// this playlist and opens it in OneDeck; Open Presentation goes back to one.
// Pictures and videos added or dropped on the form each become a presentation
// of one slide (one_display/playlist.py).
function addMedia(frm, files) {
	const uploaded = [];
	let timer = null;
	new frappe.ui.FileUploader({
		doctype: frm.doctype,
		docname: frm.doc.name,
		files,
		allow_multiple: true,
		make_attachments_public: false,
		restrictions: { allowed_file_types: ["image/*", "video/*"] },
		on_success(file) {
			uploaded.push(file.name);
			clearTimeout(timer);
			// the uploader says each file on its own; the playlist takes them together
			timer = setTimeout(async () => {
				const names = uploaded.splice(0);
				await frappe.xcall("onedesk.one_display.playlist.add_media", { playlist: frm.doc.name, files: names });
				frm.reload_doc();
			}, 800);
		},
	});
}

frappe.ui.form.on("Slide Playlist", {
	setup(frm) {
		frm.set_query("presentation", "slides", () => ({ query: "onedesk.one_deck.api.search" }));
	},
	onload_post_render(frm) {
		frm.wrapper.addEventListener("dragover", (event) => event.dataTransfer?.types?.includes("Files") && event.preventDefault());
		frm.wrapper.addEventListener("drop", (event) => {
			const files = Array.from(event.dataTransfer?.files || []);
			if (!files.length || frm.is_new()) return;
			event.preventDefault();
			addMedia(frm, files);
		});
	},
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Add Pictures and Videos"), () => addMedia(frm));
		frm.add_custom_button(__("New Presentation"), () =>
			frappe.prompt(
				[{ fieldname: "title", fieldtype: "Data", label: __("Title"), reqd: 1 }],
				async ({ title }) => {
					const made = await frappe.xcall("onedesk.one_deck.api.make", { parent: `@records/Slide Playlist/${frm.doc.name}`, title });
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
