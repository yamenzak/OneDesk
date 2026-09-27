// A person's calendar link, drawn one way wherever it is shown: Settings ›
// Calendar and OneCalendar's Subscribe. A button per app with that app's own
// mark (brand/others, registered as Custom Icons), each opening the app ready
// to add the calendar: Google and Outlook take it by its address on the web,
// and Apple opens a webcal:// one itself. Then what it carries, whether an app
// has read it, and the two things that end it. See one_calendar/feed.py.
frappe.provide("onedesk.calendar_link");

// `copy: false` where the page head already copies it.
onedesk.calendar_link.html = (link, { copy = true } = {}) => {
	const esc = frappe.utils.escape_html;
	const google = `https://calendar.google.com/calendar/render?cid=${encodeURIComponent(link.webcal)}`;
	const outlook = `https://outlook.office.com/calendar/0/addfromweb?url=${encodeURIComponent(link.https)}&name=${encodeURIComponent(link.name)}`;
	// An espresso button drawn as a link, as frappe.ui.empty_state draws one.
	const app = (href, icon, label) =>
		`<a class="es-button" href="${esc(href)}" target="_blank" rel="noopener">${frappe.utils.icon(icon, "sm")}<span class="es-button__label">${esc(label)}</span></a>`;
	const carries = (link.carries || []).map((label) => frappe.ui.badge.html({ label, theme: "gray" })).join("");
	const read = link.last_read
		? __("A calendar app last read it {0}.", [frappe.datetime.prettyDate(link.last_read)])
		: __("No calendar app has read it yet.");
	return `<div class="one-calendar-apps">
			${app(google, "google-calendar", __("Google Calendar"))}
			${app(link.webcal, "apple-calendar", __("Apple Calendar"))}
			${app(outlook, "outlook", __("Outlook"))}
			${copy ? frappe.ui.button.html({ label: __("Copy Link"), icon: "copy", attrs: { "data-calendar-copy": "1" } }) : ""}
		</div>
		${carries ? `<div class="one-calendar-carries"><span class="one-calendar-said">${esc(__("It carries"))}</span>${carries}</div>` : ""}
		<div class="one-calendar-ends">
			<span class="one-calendar-said">${esc(read)} ${esc(__("Anyone with the link can read your calendar."))}</span>
			<span class="one-calendar-end-actions">${onedesk.shell.button(__("New Link"), { "data-calendar-renew": "1" }, "ghost", "refresh-cw")}${onedesk.shell.button(
				__("Switch Off"),
				{ "data-calendar-stop": "1" },
				"ghost",
				"power",
				"red"
			)}</span>
		</div>`;
};

onedesk.calendar_link.copy = (link) => frappe.utils.copy_to_clipboard(link.https);

// `drawn` gets the new link after New Link; `stopped` runs once it is off.
onedesk.calendar_link.bind = ($root, link, { drawn, stopped }) => {
	$root.find("[data-calendar-copy]").on("click", () => onedesk.calendar_link.copy(link));
	$root.find("[data-calendar-renew]").on("click", () =>
		frappe.confirm(__("The old link stops working, so every app that reads it has to be given the new one. Make a new link?"), async () => {
			drawn(await frappe.xcall("onedesk.one_calendar.feed.renew"));
			frappe.ui.toast({ message: __("New link made. The old one no longer works."), type: "success" });
		})
	);
	$root.find("[data-calendar-stop]").on("click", () =>
		frappe.confirm(__("Switch the link off? Calendars that read it stop updating."), async () => {
			await frappe.xcall("onedesk.one_calendar.feed.stop");
			frappe.ui.toast({ message: __("Your calendar link is switched off."), type: "warning" });
			stopped();
		})
	);
};
