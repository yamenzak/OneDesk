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
