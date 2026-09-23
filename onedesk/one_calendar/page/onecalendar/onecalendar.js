// The calendar: every app's dated things as layers over one week.
//
// The layers and the entries come from one_calendar/layers.py, each read as the
// person looking, so this page draws and never decides who sees what. Which
// layers are off, and the view, are the reader's own user settings, kept under
// Event: they follow the person to another browser.

frappe.pages["onecalendar"].on_page_load = (wrapper) => {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Calendar"), single_column: true });
	wrapper.onecalendar = new onedesk.OneCalendar(page);
};

frappe.pages["onecalendar"].on_page_show = (wrapper) => {
	wrapper.onecalendar && wrapper.onecalendar.refetch();
};

frappe.provide("onedesk");

// Who may put an event on everybody's calendar; one_calendar/events.py checks
// the same list on save.
onedesk.CALENDAR_PUBLISHERS = ["Workspace Administrator", "HR Manager"];

onedesk.OneCalendar = class OneCalendar {
	constructor(page) {
		this.page = page;
		page.set_primary_action(__("New Event"), () => this.new_event());
		page.set_secondary_action(__("Subscribe"), () => this.subscribe());
		this.$body = $(`<div class="one-calendar">
			<aside class="one-calendar-layers"></aside>
			<div class="one-calendar-main"></div>
		</div>`).appendTo(page.main);
		frappe.require("calendar.bundle.js", () => this.start());
	}

	// The layers switched off go as one string: user settings are merged
	// deeply, and an array merged into a longer one keeps the old tail.
	save() {
		frappe.model.user_settings.save("Event", "OneCalendar", { view: this.saved.view, off: this.saved.off.join(",") });
	}

	async start() {
		const settings = await frappe.model.user_settings.get("Event");
		const kept = (settings && settings.OneCalendar) || {};
		this.saved = { view: kept.view, off: typeof kept.off === "string" ? kept.off.split(",").filter(Boolean) : null };
		this.layers = (await frappe.xcall("onedesk.one_calendar.layers.layers")) || [];
		this.saved.off = this.saved.off || this.layers.filter((one) => !one.on).map((one) => one.key);
		this.draw_layers();
		this.calendar = new frappe.FullCalendar(this.$body.find(".one-calendar-main")[0], {
			plugins: frappe.FullCalendar.Plugins,
			initialView: this.saved.view || "timeGridWeek",
			headerToolbar: {
				left: "prev,next today",
				center: "title",
				right: "dayGridMonth,timeGridWeek,timeGridDay,listWeek",
			},
			buttonText: { today: __("Today"), month: __("Month"), week: __("Week"), day: __("Day"), list: __("List") },
			allDayText: __("All Day"),
			noEventsText: __("Nothing on these days."),
			firstDay: frappe.datetime.get_first_day_of_the_week_index(),
			direction: frappe.utils.is_rtl() ? "rtl" : "ltr",
			height: "100%",
			nowIndicator: true,
			selectable: true,
			selectMirror: true,
			dayMaxEvents: true,
			eventDisplay: "block",
			// A half-hour event is one line tall; FullCalendar fills it with the time
			// and the title falls off the end. It is drawn a little taller, with the
			// title alone (onecalendar.css) — where it sits already says when.
			eventMinHeight: 22,
			scrollTime: "08:00:00",
			events: (info, done, failed) => this.entries(info).then(done, failed),
			select: (info) => this.new_event(info),
			eventClick: (info) => this.open(info),
			eventDrop: (info) => this.move(info),
			eventResize: (info) => this.move(info),
			eventDidMount: (info) => {
				// The whole title on hover, since a short event cuts it off.
				const said = info.event.extendedProps.description;
				info.el.title = said ? `${info.event.title}\n${said}` : info.event.title;
			},
			datesSet: (info) => {
				if (this.saved.view !== info.view.type) {
					this.saved.view = info.view.type;
					this.save();
				}
			},
		});
		this.calendar.render();
	}

	draw_layers() {
		const $side = this.$body.find(".one-calendar-layers").empty();
		for (const group of ["Mine", "Workspace"]) {
			const mine = this.layers.filter((one) => one.group === group);
			if (!mine.length) continue;
			$side.append(`<div class="one-calendar-group">${__(group)}</div>`);
			for (const one of mine) {
				const on = !this.saved.off.includes(one.key);
				$(`<label class="one-calendar-layer">
					<input type="checkbox" ${on ? "checked" : ""}>
					<span class="one-calendar-dot" style="background: var(--${one.color}-500)"></span>
					<span>${frappe.utils.escape_html(one.label)}</span>
				</label>`)
					.appendTo($side)
					.find("input")
					.on("change", (e) => {
						this.saved.off = this.saved.off.filter((key) => key !== one.key);
						if (!e.target.checked) this.saved.off.push(one.key);
						this.save();
						this.refetch();
					});
			}
		}
	}

	refetch() {
		this.calendar && this.calendar.refetchEvents();
	}

	async entries(info) {
		const keys = this.layers.map((one) => one.key).filter((key) => !this.saved.off.includes(key));
		if (!keys.length) return [];
		const last = moment(info.end).subtract(1, "day");
		const rows = await frappe.xcall("onedesk.one_calendar.layers.entries", {
			start: moment(info.start).format("YYYY-MM-DD"),
			end: last.format("YYYY-MM-DD"),
			keys,
		});
		return (rows || []).map((one) => ({
			id: one.id,
			title: one.title,
			start: one.start,
			end: one.end,
			allDay: one.all_day,
			editable: one.editable,
			backgroundColor: `var(--${one.color}-500)`,
			borderColor: `var(--${one.color}-500)`,
			textColor: "#fff",
			extendedProps: one,
		}));
	}

	open(info) {
		info.jsEvent.preventDefault();
		const one = info.event.extendedProps;
		frappe.set_route("Form", one.doctype, one.name);
	}

	move(info) {
		const one = info.event;
		const format = (when) => (when ? moment(when).format("YYYY-MM-DD HH:mm:ss") : null);
		frappe
			.xcall("onedesk.one_calendar.events.move", {
				event: one.extendedProps.name,
				start: format(one.start),
				end: format(one.end),
				all_day: one.allDay ? 1 : 0,
			})
			.catch(() => info.revert());
	}

	new_event(info) {
		const all_day = info ? info.allDay : false;
		const start = info ? moment(info.start) : moment().add(1, "hour").startOf("hour");
		let end = info ? moment(info.end) : moment(start).add(1, "hour");
		// A day picked on the month view ends at midnight after it; the event
		// ends that day.
		if (all_day) end = moment(end).subtract(1, "second");
		const may_publish = onedesk.CALENDAR_PUBLISHERS.some((role) => frappe.user.has_role(role));
		const dialog = new frappe.ui.Dialog({
			title: __("New Event"),
			fields: [
				{ fieldtype: "Data", fieldname: "subject", label: __("Subject"), reqd: 1 },
				{ fieldtype: "Check", fieldname: "all_day", label: __("All Day"), default: all_day ? 1 : 0 },
				{ fieldtype: "Datetime", fieldname: "starts_on", label: __("Starts On"), reqd: 1, default: start.format("YYYY-MM-DD HH:mm:ss") },
				{ fieldtype: "Datetime", fieldname: "ends_on", label: __("Ends On"), default: end.format("YYYY-MM-DD HH:mm:ss") },
				{ fieldtype: "Data", fieldname: "location", label: __("Location") },
				{
					fieldtype: "Check",
					fieldname: "public",
					label: __("On Everybody's Calendar"),
					hidden: may_publish ? 0 : 1,
				},
				{ fieldtype: "Small Text", fieldname: "description", label: __("Description") },
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				await frappe.db.insert({
					doctype: "Event",
					subject: values.subject,
					all_day: values.all_day,
					starts_on: values.starts_on,
					ends_on: values.ends_on,
					location: values.location,
					description: values.description,
					event_type: values.public ? "Public" : "Private",
				});
				dialog.hide();
				this.calendar.unselect();
				this.refetch();
			},
		});
		dialog.show();
	}

	// One line, a button per app, and the link. Google and Outlook each take a
	// calendar by its address in the web; Apple opens a webcal:// one itself.
	async subscribe() {
		const dialog = new frappe.ui.Dialog({ title: __("Subscribe") });
		const draw = (link) => {
			const google = `https://calendar.google.com/calendar/render?cid=${encodeURIComponent(link.webcal)}`;
			const outlook = `https://outlook.office.com/calendar/0/addfromweb?url=${encodeURIComponent(link.https)}&name=${encodeURIComponent(link.name)}`;
			// Each app's own mark, from brand/others (registered as Custom Icons).
			const button = (href, icon, label) =>
				`<a class="btn btn-default btn-sm" href="${href}" target="_blank" rel="noopener">${frappe.utils.icon(icon, "sm")} ${label}</a>`;
			dialog.$body.html(`
				<p class="text-muted small">${__("See this calendar in another app. Google Calendar updates it a few times a day, the others more often.")}</p>
				<div class="one-calendar-apps">
					${button(google, "google-calendar", __("Google Calendar"))}
					${button(link.webcal, "apple-calendar", __("Apple Calendar"))}
					${button(outlook, "outlook", __("Outlook"))}
					<button class="btn btn-default btn-sm one-calendar-copy">${__("Copy Link")}</button>
				</div>
				<p class="text-muted small one-calendar-private">
					${__("Anyone with the link can read your calendar.")}
					<a class="one-calendar-renew">${__("New Link")}</a> ·
					<a class="one-calendar-stop">${__("Switch Off")}</a>
				</p>`);
			dialog.$body.find(".one-calendar-copy").on("click", () => frappe.utils.copy_to_clipboard(link.https));
			dialog.$body.find(".one-calendar-renew").on("click", async () => {
				draw(await frappe.xcall("onedesk.one_calendar.feed.renew"));
				frappe.show_alert({ message: __("New link made. The old one no longer works."), indicator: "green" });
			});
			dialog.$body.find(".one-calendar-stop").on("click", async () => {
				await frappe.xcall("onedesk.one_calendar.feed.stop");
				frappe.show_alert({ message: __("Your calendar link is switched off."), indicator: "orange" });
				dialog.hide();
			});
		};
		draw(await frappe.xcall("onedesk.one_calendar.feed.mine"));
		dialog.show();
	}
};
