// OneCalendar's ControlCenter (docs/ONE.md): Your Calendar Link, the
// private address another calendar app subscribes to, for everybody
// (one_calendar/control.py, one_calendar/feed.py).

onedesk.CalendarSection = class CalendarSection extends onedesk.CenterSection {
	static API = "onedesk.one_calendar.control.";
	static HERE = "onecalendar";
	static LABEL = "ControlCenter";

	draw_link(data) {
		const $body = $(`<div class="os-calendar"></div>`).appendTo(this.$content);
		const draw = (link) => {
			if (!data.allowed) {
				$body.html(`<div class="one-shell-quiet">${__("Calendar links are turned off for this workspace.")}</div>`);
				return;
			}
			if (!link) {
				$body.html(`<div class="one-shell-quiet">${__("No calendar link")}</div>`);
				this.page.set_primary_action(__("Create Link"), async () => draw(await frappe.xcall("onedesk.one_calendar.feed.mine")), "link");
				return;
			}
			$body.html(onedesk.calendar_link.html(link, { copy: false }));
			onedesk.calendar_link.bind($body, link, { drawn: draw, stopped: () => draw(null) });
			this.page.set_primary_action(__("Copy Link"), () => onedesk.calendar_link.copy(link), "copy");
		};
		draw(data.link);
	}
};

onedesk.centers.part("settings", onedesk.names.of("one_calendar"), {
	sections: () => [
		{
			group: null,
			items: [
				{
					id: "link",
					label: __("Your Calendar Link"),
					icon: "link",
					description: __("Your {0} in Google Calendar, Apple Calendar or Outlook, through a private link.", [onedesk.names.of("one_calendar")]),
					section: onedesk.CalendarSection,
				},
			],
		},
	],
});

// Its foot (docs/READY.md, mechanism 5): Settings, the tour, Help and the
// version at the foot of its rail, on whichever of its screens is open. The
// calendar is a desk page, so the window draws it (module_foot).
$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.interface.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== onedesk.names.sidebar("one_calendar")) return;
		win.module_foot({ module: onedesk.names.of("one_calendar"), settings: () => onedesk.centers.open("settings", { module: onedesk.names.of("one_calendar") }) });
		onedesk.interface.nav.place();
	}, 0)
);
