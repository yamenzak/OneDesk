// The calendar: every app's dated things as layers over one week.
//
// The layers and the entries come from one_calendar/layers.py, each read as the
// person looking, so this page draws and never decides who sees what. Which
// layers are off, and the view, are the reader's own user settings, kept under
// Event: they follow the person to another browser.
//
// With ?doctype=Project&name=PROJ-0004 it is that record's own calendar: only
// the layers that can draw one (a project's tasks, the events about it), and
// nothing it changes is saved as the reader's main calendar.

frappe.pages["onecalendar"].on_page_load = (wrapper) => {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Calendar"), single_column: true });
	wrapper.onecalendar = new onedesk.OneCalendar(page);
};

frappe.pages["onecalendar"].on_page_show = (wrapper) => {
	wrapper.onecalendar && wrapper.onecalendar.show();
};

frappe.provide("onedesk");

// Who may put an event on everybody's calendar; one_calendar/events.py checks
// the same list on save.
onedesk.CALENDAR_PUBLISHERS = ["Workspace Administrator", "HR Manager"];

onedesk.OneCalendar = class OneCalendar {
	constructor(page) {
		this.page = page;
		// The list view's own button: same label, same short label, same icon.
		page.set_primary_action(
			{ label: __("Add {0}", [__("Event")]), short_label: __("Add") },
			() => this.new_event(),
			"plus"
		);
		this.about = this.narrowed();
		this.$body = $(`<div class="one-calendar">
			<aside class="one-calendar-layers"></aside>
			<div class="one-calendar-main">
				<div class="one-calendar-toolbar"></div>
				<div class="one-calendar-grid"></div>
			</div>
		</div>`).appendTo(page.main);
		frappe.require("calendar.bundle.js", () => this.start());
	}

	// The layers switched off go as one string: user settings are merged
	// deeply, and an array merged into a longer one keeps the old tail.
	save() {
		// Opened straight on a record's calendar, the main calendar's layers were
		// never read, so they are left as they were rather than saved as none.
		const off = this.saved.off ? { off: this.saved.off.join(",") } : {};
		frappe.model.user_settings.save("Event", "OneCalendar", { view: this.saved.view, ...off });
	}

	// The record this is the calendar of, from the address, or null.
	narrowed() {
		const { doctype, name } = frappe.utils.get_query_params();
		return doctype && name ? { doctype, name } : null;
	}

	// Coming back to the page, perhaps for another record or for none.
	async show() {
		if (!this.calendar) return;
		const about = this.narrowed();
		if (JSON.stringify(about) !== JSON.stringify(this.about)) {
			this.about = about;
			await this.read_layers();
		}
		this.refetch();
	}

	async read_layers() {
		this.layers = (await frappe.xcall("onedesk.one_calendar.layers.layers", this.about || {})) || [];
		if (!this.about) this.saved.off = this.saved.off || this.layers.filter((one) => !one.on).map((one) => one.key);
		this.draw_layers();
		// A record's calendar is named after it, and has no link to subscribe to:
		// the link is the reader's own calendar.
		this.page.clear_secondary_action();
		// The heading is the breadcrumb trail, which names the record and leads
		// back to it.
		if (this.about) {
			const { doctype, name } = this.about;
			const title = (await frappe.utils.fetch_link_title(doctype, name)) || name;
			this.page.set_title(__("{0} Calendar", [title]));
			frappe.breadcrumbs.add({
				type: "Custom",
				label: frappe.utils.escape_html(__("{0} Calendar", [title])),
				route: `/desk/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}`,
			});
		} else {
			this.page.set_title(__("Calendar"));
			frappe.breadcrumbs.add({ type: "Custom", label: __("Calendar") });
			this.page.set_secondary_action(__("Subscribe"), () => this.subscribe(), "rss");
		}
	}

	// Layers switched off on a record's calendar are off for this visit only.
	off() {
		return this.about ? this.off_here || [] : this.saved.off;
	}

	async start() {
		const settings = await frappe.model.user_settings.get("Event");
		const kept = (settings && settings.OneCalendar) || {};
		this.saved = { view: kept.view, off: typeof kept.off === "string" ? kept.off.split(",").filter(Boolean) : null };
		await this.read_layers();
		this.draw_toolbar();
		this.calendar = new frappe.FullCalendar(this.$body.find(".one-calendar-grid")[0], {
			plugins: frappe.FullCalendar.Plugins,
			initialView: this.saved.view || "timeGridWeek",
			headerToolbar: false,
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
				this.$title.find(".es-button__label").text(info.view.title);
				const now = new Date();
				this.$today.prop("disabled", info.view.activeStart <= now && now < info.view.activeEnd);
				if (this.saved.view !== info.view.type) {
					this.saved.view = info.view.type;
					this.save();
				}
			},
		});
		this.calendar.render();
	}

	// The desk's own calendar toolbar (frappe/views/calendar): the arrows, the
	// title that opens a date picker, Today, and the views as TabButtons.
	draw_toolbar() {
		this.$title = frappe.ui.button({ label: __("Calendar"), variant: "ghost", css_class: "text-lg-medium text-ink-gray-7" });
		this.jumper = new frappe.ui.Popover({
			trigger: this.$title,
			content: () => this.date_jumper(),
			css_class: "calendar-date-jumper",
		});
		this.views = new frappe.ui.TabButtons({
			label: __("Calendar View"),
			options: [
				{ label: __("Month"), value: "dayGridMonth" },
				{ label: __("Week"), value: "timeGridWeek" },
				{ label: __("Day"), value: "timeGridDay" },
				{ label: __("List"), value: "listWeek" },
			],
			value: this.saved.view || "timeGridWeek",
			on_change: (view) => this.calendar.changeView(view),
		});
		this.$today = frappe.ui.button({ label: __("Today"), onclick: () => this.calendar.today() });
		this.$body.find(".one-calendar-toolbar").append(
			frappe.ui.button({ icon: "chevron-left", variant: "ghost", title: __("Previous"), onclick: () => this.calendar.prev() }),
			this.$title,
			frappe.ui.button({ icon: "chevron-right", variant: "ghost", title: __("Next"), onclick: () => this.calendar.next() }),
			$('<div class="grow"></div>'),
			this.$today,
			this.views.$el,
		);
	}

	// Pick a day, and the calendar goes there in the view it is in.
	date_jumper() {
		const wrapper = document.createElement("div");
		let lang = (frappe.boot.user && frappe.boot.user.language) || "en";
		if (!$.fn.datepicker.language[lang]) lang = "en";
		const months = this.calendar.view.type === "dayGridMonth";
		let ready = false;
		$(wrapper).datepicker({
			language: lang,
			firstDay: frappe.datetime.get_first_day_of_the_week_index(),
			...(months ? { view: "months", minView: "months" } : {}),
			onSelect: (_formatted, day) => {
				if (!ready || !day) return;
				this.calendar.gotoDate(day);
				this.jumper.close();
			},
		});
		$(wrapper).data("datepicker").selectDate(this.calendar.getDate());
		ready = true;
		return wrapper;
	}

	draw_layers() {
		const $side = this.$body.find(".one-calendar-layers").empty();
		for (const group of ["Mine", "Workspace"]) {
			const mine = this.layers.filter((one) => one.group === group);
			if (!mine.length) continue;
			$side.append(`<div class="one-calendar-group">${__(group)}</div>`);
			for (const one of mine) {
				const on = !this.off().includes(one.key);
				$(`<label class="one-calendar-layer">
					<input type="checkbox" ${on ? "checked" : ""}>
					<span class="one-calendar-dot" style="background: var(--ink-${one.color}-7)"></span>
					<span>${frappe.utils.escape_html(one.label)}</span>
				</label>`)
					.appendTo($side)
					.find("input")
					.on("change", (e) => {
						const off = this.off().filter((key) => key !== one.key);
						if (!e.target.checked) off.push(one.key);
						if (this.about) {
							this.off_here = off;
						} else {
							this.saved.off = off;
							this.save();
						}
						this.refetch();
					});
			}
		}
	}

	refetch() {
		this.calendar && this.calendar.refetchEvents();
	}

	async entries(info) {
		const keys = this.layers.map((one) => one.key).filter((key) => !this.off().includes(key));
		if (!keys.length) return [];
		const last = moment(info.end).subtract(1, "day");
		const rows = await frappe.xcall("onedesk.one_calendar.layers.entries", {
			start: moment(info.start).format("YYYY-MM-DD"),
			end: last.format("YYYY-MM-DD"),
			keys,
			...(this.about || {}),
		});
		return (rows || []).map((one) => ({
			id: one.id,
			title: one.title,
			start: one.start,
			end: one.end,
			allDay: one.all_day,
			editable: one.editable,
			durationEditable: one.resizable,
			// The desk calendar's colours: a tinted surface and the family's ink,
			// both tokens, so they turn with the dark theme.
			backgroundColor: `var(--surface-${one.color}-1)`,
			borderColor: `var(--surface-${one.color}-1)`,
			textColor: `var(--ink-${one.color}-7)`,
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
			.xcall("onedesk.one_calendar.layers.move", {
				key: one.extendedProps.layer,
				name: one.extendedProps.name,
				start: format(one.start),
				end: format(one.end),
				all_day: one.allDay ? 1 : 0,
			})
			// A task dragged moves its start too, so what is drawn is read again.
			.then(() => this.refetch(), () => info.revert());
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
					// Made on a record's calendar, it is about that record.
					...(this.about ? { reference_doctype: this.about.doctype, reference_docname: this.about.name } : {}),
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
			// Each app's own mark, from brand/others (registered as Custom Icons), on
			// an espresso button drawn as a link, as frappe.ui.empty_state draws one.
			const button = (href, icon, label) =>
				`<a class="es-button" href="${href}" target="_blank" rel="noopener">${frappe.utils.icon(icon, "sm")}<span class="es-button__label">${label}</span></a>`;
			dialog.$body.html(`
				<p class="text-p-sm one-calendar-said">${__("See this calendar in another app. Google Calendar updates it a few times a day, the others more often.")}</p>
				<div class="one-calendar-apps">
					${button(google, "google-calendar", __("Google Calendar"))}
					${button(link.webcal, "apple-calendar", __("Apple Calendar"))}
					${button(outlook, "outlook", __("Outlook"))}
					${frappe.ui.button.html({ label: __("Copy Link"), icon: "copy", css_class: "one-calendar-copy" })}
				</div>
				<p class="text-p-sm one-calendar-said one-calendar-private">
					${__("Anyone with the link can read your calendar.")}
					<a class="one-calendar-renew">${__("New Link")}</a> ·
					<a class="one-calendar-stop">${__("Switch Off")}</a>
				</p>`);
			dialog.$body.find(".one-calendar-copy").on("click", () => frappe.utils.copy_to_clipboard(link.https));
			dialog.$body.find(".one-calendar-renew").on("click", async () => {
				draw(await frappe.xcall("onedesk.one_calendar.feed.renew"));
				frappe.ui.toast({ message: __("New link made. The old one no longer works."), type: "success" });
			});
			dialog.$body.find(".one-calendar-stop").on("click", async () => {
				await frappe.xcall("onedesk.one_calendar.feed.stop");
				frappe.ui.toast({ message: __("Your calendar link is switched off."), type: "warning" });
				dialog.hide();
			});
		};
		draw(await frappe.xcall("onedesk.one_calendar.feed.mine"));
		dialog.show();
	}
};
