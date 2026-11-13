frappe.provide("onedesk.calendar_link");

onedesk.calendar_link.html = (link, { copy = true, ends = true } = {}) => {
	const esc = frappe.utils.escape_html;
	const google = `https://calendar.google.com/calendar/render?cid=${encodeURIComponent(link.webcal)}`;
	const outlook = `https://outlook.office.com/calendar/0/addfromweb?url=${encodeURIComponent(link.https)}&name=${encodeURIComponent(link.name)}`;
	const app = (href, icon, label) =>
		`<a class="es-button" href="${esc(href)}" target="_blank" rel="noopener">${frappe.utils.icon(icon, "sm")}<span class="es-button__label">${esc(label)}</span></a>`;
	const carries = (link.carries || []).map((label) => frappe.ui.badge.html({ label, theme: "gray" })).join("");
	const read = link.last_read
		? __("Last synced {0}.", [frappe.datetime.prettyDate(link.last_read)])
		: __("Not synced yet.");
	return `<div class="one-calendar-apps">
			${app(google, "google-calendar", __("Google Calendar"))}
			${app(link.webcal, "apple-calendar", __("Apple Calendar"))}
			${app(outlook, "outlook", __("Outlook"))}
			${copy ? frappe.ui.button.html({ label: __("Copy Link"), icon: "copy", attrs: { "data-calendar-copy": "1" } }) : ""}
		</div>
		${carries ? `<div class="one-calendar-carries"><span class="one-calendar-said">${esc(__("Includes"))}</span>${carries}</div>` : ""}
		<div class="one-calendar-ends">
			<span class="one-calendar-said">${esc(read)} ${esc(__("Anyone with the link can read your calendar."))}</span>
			${
				ends
					? `<span class="one-calendar-end-actions">${onedesk.shell.button(__("New Link"), { "data-calendar-renew": "1" }, "ghost", "refresh-cw")}${onedesk.shell.button(
							__("Switch Off"),
							{ "data-calendar-stop": "1" },
							"ghost",
							"power",
							"red"
					  )}</span>`
					: ""
			}
		</div>`;
};

onedesk.calendar_link.copy = (link) => frappe.utils.copy_to_clipboard(link.https);

onedesk.calendar_link.renew = (drawn) =>
	frappe.confirm(__("Create a new link? The old one stops working in every app that uses it."), async () => {
		drawn(await frappe.xcall("onedesk.one_calendar.feed.renew"));
		frappe.ui.toast({ message: __("New link created"), type: "success" });
	});

onedesk.calendar_link.stop = (stopped) =>
	frappe.confirm(__("Switch off the link? Calendars that use it stop updating."), async () => {
		await frappe.xcall("onedesk.one_calendar.feed.stop");
		frappe.ui.toast({ message: __("Link switched off"), type: "warning" });
		stopped();
	});

onedesk.calendar_link.bind = ($root, link, { drawn, stopped }) => {
	$root.find("[data-calendar-copy]").on("click", () => onedesk.calendar_link.copy(link));
	$root.find("[data-calendar-renew]").on("click", () => onedesk.calendar_link.renew(drawn));
	$root.find("[data-calendar-stop]").on("click", () => onedesk.calendar_link.stop(stopped));
};
