// OneCalendar's ControlCenter (docs/ONE.md): Your Calendar Link, the
// private address another calendar app subscribes to, for everybody
// (one_calendar/control.py, one_calendar/feed.py).
frappe.provide("onedesk.calendar_control");

onedesk.CalendarSection = class CalendarSection extends onedesk.CenterSection {
	static API = "onedesk.one_calendar.control.";
	static HERE = "onecalendar";
	static LABEL = "ControlCenter";

	draw_link(data) {
		const how = onedesk.oneai.button(
			__("How Do I Add It?"),
			__("How do I add my calendar to Google Calendar, Apple Calendar or Outlook?")
		);
		const $card = $(
			onedesk.shell.section(
				__("Calendar Link"),
				`<div class="os-calendar"></div><div class="one-shell-actions">${how}</div>`
			)
		).appendTo(this.$content);
		const draw = (link) => {
			const $body = $card.find(".os-calendar");
			if (!data.allowed) {
				$body.html(`<div class="one-shell-quiet">${__("Calendar links are turned off for this workspace.")}</div>`);
				$card.find(".one-shell-actions").remove();
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

onedesk.calendar_control.open = ({ at = null } = {}) => {
	const dialog = onedesk.module_settings.open({
		module: "OneCalendar",
		tabs: [
			{
				group: null,
				items: [
					onedesk.center_section.tab(onedesk.CalendarSection, {
						id: "link",
						label: __("Your Calendar Link"),
						icon: "link",
						about: __("Your OneCalendar in Google Calendar, Apple Calendar or Outlook, through a private link."),
					}),
				],
			},
		],
		default_tab: at,
	});
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneCalendar = onedesk.calendar_control.open;
