const DRAWN = [
	"title",
	"runs",
	"record_doctype",
	"view",
	"place",
	"event",
	"cron",
	"explanation",
	"asked",
	"asked_by_name",
	"review",
	"review_note",
];

const WHEN = {
	"Before Insert": (kind) => __("Before a new {0} is saved for the first time", [kind]),
	"Before Validate": (kind) => __("Each time a {0} is saved, before it is checked", [kind]),
	"Before Save": (kind) => __("Each time a {0} is saved, before it is written", [kind]),
	"After Insert": (kind) => __("After a new {0} is saved for the first time", [kind]),
	"After Save": (kind) => __("After a {0} is saved", [kind]),
	"Before Submit": (kind) => __("Before a {0} is submitted", [kind]),
	"After Submit": (kind) => __("After a {0} is submitted", [kind]),
	"Before Cancel": (kind) => __("Before a {0} is cancelled", [kind]),
	"After Cancel": (kind) => __("After a {0} is cancelled", [kind]),
	"Before Save (Submitted Document)": (kind) =>
		__("Before a submitted {0} is changed and saved", [kind]),
	"After Save (Submitted Document)": (kind) =>
		__("After a submitted {0} is changed and saved", [kind]),
	"Before Delete": (kind) => __("Before a {0} is deleted", [kind]),
	"After Delete": (kind) => __("After a {0} is deleted", [kind]),
	"Every Hour": () => __("Every hour"),
	"Every Day": () => __("Every day"),
	"Every Week": () => __("Every week"),
	"Every Month": () => __("Every month"),
	"Scheduled": (kind, cron) => __("On the schedule {0}", [cron || ""]),
};

const PLACES = {
	"onemail.conversation": () => __("In {0}, when a conversation opens", [onedesk.names.of("one_mail")]),
	"onemail.compose": () => __("When an email is written"),
	"record_head.drawn": (kind) => __("In the header of each {0}", [kind]),
	"onecloud.file": () => __("In {0}, when a file preview opens", [onedesk.names.of("one_cloud")]),
	"intake.reading": () => __("In Documents, when a document opens"),
	"onecrm.board": () => __("On the {0} pipeline board", [onedesk.names.of("one_crm")]),
	"space.home": () => __("On each space's home page"),
	"onecalendar.event": () => __("In {0}, when an event opens", [onedesk.names.of("one_calendar")]),
};

const FIXED = "Fixed: ";

frappe.ui.form.on("Extension", {
	refresh(frm) {
		frm.disable_save();
		frm.sidebar?.sidebar
			.find(".form-assignments, .form-attachments, .form-tags, .form-shared")
			.addClass("hidden");
		frm.toggle_display(DRAWN, false);
		frm.set_df_property("code", "label", "");
		frm.events.draw(frm);
		frm.events.offer_draft(frm);
	},

	offer_draft(frm) {
		const draft = frm.doc.draft && JSON.parse(frm.doc.draft);
		if (!draft) return;
		const call = (method) =>
			frappe
				.xcall(`onedesk.one_studio.extensions.${method}`, { extension: frm.doc.name })
				.then(() => frm.reload_doc());
		if (draft.review === "Passed") {
			frm.add_custom_button(__("Use New Version"), () => call("use_draft"));
			frm.change_custom_button_type(__("Use New Version"), null, "primary");
		}
		frm.add_custom_button(__("Discard New Version"), () =>
			frappe.confirm(__("Discard the new version? The one that is on stays as it is."), () => call("drop_draft")),
		);
	},

	draw(frm) {
		const field = frm.fields_dict.summary;
		if (!field || frm.is_new()) return;
		const esc = frappe.utils.escape_html;
		const shell = onedesk.shell;
		const doc = frm.doc;
		const kind = __(doc.record_doctype || "");
		const text = (words) => `<div class="one-extension-text">${esc(words)}</div>`;
		const where =
			doc.runs === "On Server"
				? (WHEN[doc.event] || (() => __(doc.event || "")))(kind, doc.cron)
				: doc.view === "Page"
				? (PLACES[doc.place] || (() => doc.place || ""))(kind)
				: doc.view === "List"
					? __("On the {0} list", [kind])
					: __("On the {0} form", [kind]);

		const sections = [];
		if (doc.review === "Refused" && doc.explanation) {
			sections.push(shell.section(__("What It Does"), text(doc.explanation)));
		}
		const record =
			doc.record_doctype && doc.view !== "Page"
				? ` · <a href="/desk/${frappe.router.slug(doc.record_doctype)}">${esc(kind)}</a>`
				: "";
		sections.push(
			shell.section(
				__("Where It Runs"),
				shell.row({
					title: esc(where),
					sub: esc(doc.runs === "On Server" ? __("On the server") : __("In the browser")) + record,
				}),
			),
		);

		const asked = (doc.asked || "").split(/\n\s*\n/).filter((one) => one.trim());
		const by = [
			doc.asked_by_name ? esc(doc.asked_by_name) : "",
			doc.written_on ? frappe.datetime.comment_when(doc.written_on) : "",
		]
			.filter(Boolean)
			.join(" · ");
		if (asked.length) {
			const said = asked.map((one, i) => {
				const fixed = one.startsWith(FIXED);
				const mark = fixed
					? frappe.ui.badge.html({ label: __("Fixed"), theme: "blue" })
					: i === 0 && by
						? `<span class="one-shell-quiet">${by}</span>`
						: "";
				return `<div class="one-extension-asked">${text(fixed ? one.slice(FIXED.length) : one)}${mark}</div>`;
			});
			sections.push(shell.section(__("Asked"), said.join("")));
		}

		if (doc.review) {
			const badge = frappe.ui.badge.html({
				label: __(doc.review),
				theme: doc.review === "Passed" ? "green" : "red",
			});
			sections.push(
				shell.section(
					__("Review"),
					doc.review_note ? text(doc.review_note) : "",
					"",
					badge,
				),
			);
		}
		const draft = doc.draft && JSON.parse(doc.draft);
		if (draft) {
			const badge = frappe.ui.badge.html({
				label: __(draft.review),
				theme: draft.review === "Passed" ? "green" : "red",
			});
			sections.unshift(
				shell.section(
					__("New Version"),
					text(
						draft.review === "Passed"
							? __("{0} wrote a new version. The one that is on keeps running until you use it.", [onedesk.names.of("one_ai")])
							: __("{0} wrote a new version, and the review refused it. The one that is on keeps running.", [onedesk.names.of("one_ai")]),
					) + (draft.review_note ? text(draft.review_note) : ""),
					"",
					badge,
				),
			);
		}
		field.$wrapper.html(`<div class="one-extension">${sections.join("")}</div>`);
	},
});
