// An extension, from the administrator's side. Everything on it is OneAI's or
// the review's, so there is nothing to type and no Save: Turn On and Turn Off
// are its Record Head's verbs (one_studio/heads.py), and changing it is asking
// OneAI. Nothing is attached to it, handed to anybody or shared: an extension
// is the administrators' own.
//
// Its fields stay on the doctype for the list, the filters and OneAI. On the
// form they are read as a page, in the Summary field, rather than as a column
// of greyed-out inputs.
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

// When each event runs, said of the kind of record it runs on.
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
	// Scheduled: on its own, over the records it finds.
	"Every Hour": () => __("Every hour"),
	"Every Day": () => __("Every day"),
	"Every Week": () => __("Every week"),
	"Every Month": () => __("Every month"),
	"On a Schedule": (kind, cron) => __("On the schedule {0}", [cron || ""]),
};

// Where a page extension runs, said of its place (one_studio/places.py).
const PLACES = {
	"onemail.conversation": () => __("In OneMail, when a conversation opens"),
	"onemail.compose": () => __("When an email is written"),
	"record_head.drawn": (kind) => __("In the header of each {0}", [kind]),
	"onetask.listed": () => __("On My Tasks"),
	"onecloud.file": () => __("In OneCloud, when a file preview opens"),
	"intake.reading": () => __("In OneIntake, when a document opens"),
	"onecrm.board": () => __("On the OneCRM pipeline board"),
	"space.home": () => __("On each space's home page"),
	"onecalendar.event": () => __("In OneCalendar, when an event opens"),
};

// How mend.py marks each fix it adds to the request.
const FIXED = "Fixed: ";

frappe.ui.form.on("Extension", {
	refresh(frm) {
		frm.disable_save();
		frm.sidebar?.sidebar
			.find(".form-assignments, .form-attachments, .form-tags, .form-shared")
			.addClass("hidden");
		frm.toggle_display(DRAWN, false);
		// The Code section's title already says it.
		frm.set_df_property("code", "label", "");
		frm.events.draw(frm);
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
		// The head says what it does, unless the review refused it: then the
		// head says why, and what it does is said here.
		if (doc.review === "Refused" && doc.explanation) {
			sections.push(shell.section(__("What It Does"), text(doc.explanation)));
		}
		// Where, in words, then on the server or the screen; the record type
		// links to its list, except where a page is the place.
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

		// The request, then each fix OneAI made to it.
		const asked = (doc.asked || "").split(/\n\s*\n/).filter((one) => one.trim());
		// comment_when is frappe's own markup, a timestamp that keeps itself current.
		const by = [
			doc.asked_by_name ? esc(doc.asked_by_name) : "",
			doc.written_on ? frappe.datetime.comment_when(doc.written_on) : "",
		]
			.filter(Boolean)
			.join(" · ");
		if (asked.length) {
			// What was asked, then each fix, as the words they were: prose, so
			// paragraphs, not rows.
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
		field.$wrapper.html(`<div class="one-extension">${sections.join("")}</div>`);
	},
});
