// What the pack has said of each kind, and the two ways to fill it.
frappe.ui.form.on("Voice Pack", {
	refresh(frm) {
		const covers = frm.doc.__onload?.covers || {};
		const rows = Object.entries(covers).map(
			([kind, { made, of }]) => `<div class="flex justify-between py-1"><span>${__(kind)}</span><span class="text-ink-gray-5">${__("{0} of {1}", [made, of])}</span></div>`
		);
		frm.get_field("covers").$wrapper.html(`<div class="text-base">${rows.join("")}</div>`);
		if (frm.is_new()) return;
		const missing = Object.values(covers).reduce((sum, { made, of }) => sum + of - made, 0);
		if (missing) {
			frm.add_custom_button(__("Record Missing Clips"), () =>
				frappe.xcall("onedesk.one_display.packs.make", { name: frm.doc.name }).then((count) =>
					frappe.show_alert({ message: __("Recording {0} clips.", [count]), indicator: "blue" })
				)
			);
		}
		if (frm.doc.made) {
			frm.add_custom_button(__("Re-record All"), () =>
				frappe.confirm(__("Re-record every clip in this pack? Existing clips are replaced."), () =>
					frappe.xcall("onedesk.one_display.packs.again", { name: frm.doc.name }).then((count) =>
						frappe.show_alert({ message: __("Re-recording {0} clips.", [count]), indicator: "blue" })
					)
				)
			);
		}
	},
});
