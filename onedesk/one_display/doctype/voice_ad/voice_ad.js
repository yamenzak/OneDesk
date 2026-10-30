// An ad is said in OneAI's voice once it has a recording; Make the Recording
// asks for one in the ad's tone, voice and language.
frappe.ui.form.on("Voice Ad", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.audio) frm.add_custom_button(__("Listen"), () => new Audio(frm.doc.audio).play());
		if (onedesk.apps?.ai?.()) {
			frm.add_custom_button(
				frm.doc.audio ? __("Make It Again") : __("Make the Recording"),
				() =>
					frappe
						.xcall("onedesk.one_display.voices.record", { ad: frm.doc.name }, undefined, { freeze: true, freeze_message: __("OneAI is recording the ad") })
						.then(() => frm.reload_doc()),
				__("OneAI")
			);
		}
	},
});
