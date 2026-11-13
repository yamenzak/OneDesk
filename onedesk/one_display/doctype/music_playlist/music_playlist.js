// Every screen of a channel plays the same second of the same track, which
// it can only do knowing each track's length: the browser reads it here.
frappe.provide("onedesk.display");

onedesk.display.measure = (url, kind) =>
	new Promise((done) => {
		const media = document.createElement(kind);
		media.preload = "metadata";
		media.onloadedmetadata = () => done(Number.isFinite(media.duration) ? media.duration : 0);
		media.onerror = () => done(0);
		media.src = url;
	});

frappe.ui.form.on("Display Track", {
	file(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.file) return;
		onedesk.display.measure(row.file, "audio").then((seconds) => {
			frappe.model.set_value(cdt, cdn, "duration", Math.round(seconds * 10) / 10);
			if (!row.title) frappe.model.set_value(cdt, cdn, "title", row.file.split("/").pop().replace(/\.[^.]+$/, ""));
		});
	},
});

// OneAI writes a piece of music in the background; it arrives paused at the
// end of the playlist, with a notification.
frappe.ui.form.on("Music Playlist", {
	refresh(frm) {
		if (frm.is_new() || !onedesk.apps?.ai?.()) return;
		frm.add_custom_button(
			__("Make Music"),
			() =>
				frappe.prompt(
					[{ fieldname: "description", fieldtype: "Small Text", label: __("Description"), reqd: 1 }],
					({ description }) =>
						frappe
							.xcall("onedesk.one_display.make.music", { playlist: frm.doc.name, description })
							.then(() => frappe.show_alert({ message: __("{0} is generating the music. You will be notified when it is added to the playlist.", [onedesk.names.of("one_ai")]), indicator: "blue" })),
					__("Make Music"),
					__("Make")
				),
			onedesk.names.of("one_ai")
		);
	},
});
