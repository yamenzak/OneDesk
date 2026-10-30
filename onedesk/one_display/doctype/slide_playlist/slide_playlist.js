// A video slide runs for its own length unless a length is given.
frappe.ui.form.on("Display Slide", {
	file(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.kind !== "Video" || !row.file) return;
		const video = document.createElement("video");
		video.preload = "metadata";
		video.onloadedmetadata = () => {
			if (Number.isFinite(video.duration)) frappe.model.set_value(cdt, cdn, "duration", Math.ceil(video.duration));
		};
		video.src = row.file;
	},
});

// OneAI makes a picture or designs a slide from a sentence; either arrives
// as a new slide at the end, to look at before saving. A video takes minutes,
// so it is made in the background and arrives paused, with a notification.
frappe.ui.form.on("Slide Playlist", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Design Slides"), () => frappe.set_route("display-slides", frm.doc.name));
			frm.change_custom_button_type(__("Design Slides"), null, "primary");
		}
		if (!onedesk.apps?.ai?.()) return;
		const ask = (title, fieldname, label, then) =>
			frappe.prompt([{ fieldname, fieldtype: "Small Text", label, reqd: 1 }], (values) => then(values[fieldname]), title, __("Make"));
		frm.add_custom_button(
			__("Make a Picture"),
			() =>
				ask(__("Make a Picture"), "description", __("What it shows"), (description) =>
					frappe.xcall("onedesk.one_display.make.picture", { description }).then((file) => {
						frm.add_child("slides", { kind: "Image", file, title: description.slice(0, 140), duration: 10 });
						frm.refresh_field("slides");
						frm.dirty();
					})
				),
			__("OneAI")
		);
		frm.add_custom_button(
			__("Design a Slide"),
			() =>
				ask(__("Design a Slide"), "description", __("What it says and how it looks"), (description) =>
					frappe.xcall("onedesk.one_display.make.design", { description }).then((made) => {
						frm.add_child("slides", {
							kind: "Design",
							design: JSON.stringify(made.design),
							html: made.html,
							title: description.slice(0, 140),
							duration: 12,
						});
						frm.refresh_field("slides");
						frm.dirty();
					})
				),
			__("OneAI")
		);
		if (frm.is_new()) return;
		frm.add_custom_button(
			__("Make a Video"),
			() =>
				ask(__("Make a Video"), "description", __("What it shows"), (description) =>
					frappe
						.xcall("onedesk.one_display.make.video", { playlist: frm.doc.name, description })
						.then(() => frappe.show_alert({ message: __("OneAI is making the video. You will be told when it is in the playlist."), indicator: "blue" }))
				),
			__("OneAI")
		);
	},
});
