// OneAI's verbs on the hiring walk. What they do is one_hr/hiring.py; these
// only ask for it, and say that the answer arrives on its own — the job runs in
// the background and the form reloads when OneAI has written to it.
frappe.provide("onedesk.hiring");

onedesk.hiring.ask = (method, args, said) => {
	frappe.call({ method: `onedesk.one_hr.hiring.${method}`, args }).then(() => {
		frappe.show_alert({ message: said, indicator: "blue" }, 7);
	});
};

frappe.ui.form.on("Job Applicant", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.job_title || !frm.perm[0]?.write) return;
		frm.add_custom_button(
			__("Screen again"),
			() =>
				onedesk.hiring.ask(
					"screen_again",
					{ applicant: frm.doc.name },
					__("OneAI is reading the CV. This page updates when it is done."),
				),
			__("OneAI"),
		);
	},
});

frappe.ui.form.on("Job Opening", {
	refresh(frm) {
		if (frm.is_new() || !frm.perm[0]?.write) return;
		frm.add_custom_button(
			__("Rank applicants again"),
			() =>
				onedesk.hiring.ask(
					"rank_again",
					{ opening: frm.doc.name },
					__("OneAI is placing everybody again. The applicant list updates when it is done."),
				),
			__("OneAI"),
		);
	},
});
