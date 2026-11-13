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
