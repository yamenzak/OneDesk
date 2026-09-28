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
	// The layers are their own navigation, as OneMail's mailboxes are: no rail
	// panel beside them. What the rail held is at the foot of the layers.
	const page = onedesk.shell.page(wrapper, __("OneCalendar"), { hide_sidebar: true });
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
		this.about = this.narrowed();
		// The layers in a pane of their own beside the week, the week's own
		// toolbar in its pane's head: the shell's panes, fitted to the window.
		// The pane is the page's only sidebar, as OneMail's mailboxes are: New
		// Event on top, the layers, and what the rail held at the foot.
		const panes = onedesk.shell.panes(page.$shell, [{ key: "layers", width: 236 }, { key: "week" }]);
		const $side = $(`<div class="one-calendar-side"></div>`)
			.attr({ role: "navigation", "aria-label": __("Layers") })
			.appendTo(panes.layers);
		frappe.ui
			.button({ label: __("New Event"), icon: "plus", variant: "solid", css_class: "one-calendar-new", onclick: () => this.new_event() })
			.appendTo($side);
		this.$layers = $(`<div class="one-calendar-layers"></div>`).appendTo($side);
		this.$foot = $(`<div class="one-calendar-foot"></div>`).appendTo($side);
		this.$toolbar = onedesk.shell.pane_head(panes.week);
		this.$grid = $(`<div class="one-calendar one-calendar-grid"></div>`).appendTo(panes.week);
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
		this.draw_foot();
		// The heading is the breadcrumb trail, which names the record and leads
		// back to it.
		if (this.about) {
			const { doctype, name } = this.about;
			const title = (await frappe.utils.fetch_link_title(doctype, name)) || name;
			// "Client Example Ltd / Calendar": the record leads back to itself.
			this.page.set_title(__("Calendar"));
			onedesk.shell.trail(title, `/desk/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}`, __("Calendar"));
		} else {
			this.page.set_title(__("OneCalendar"));
			onedesk.shell.name(__("OneCalendar"));
		}
	}

	// What the rail held, under the layers: every event as a list, the
	// deadlines, the link for another calendar app, and setup for those who
	// may. A record's calendar has no link: the link is the reader's own.
	draw_foot() {
		const $foot = this.$foot.empty();
		const link = (label, icon, onclick) =>
			frappe.ui.button({ label, icon, variant: "ghost", css_class: "one-calendar-link", onclick }).appendTo($foot);
		link(__("All Events"), "list", () => frappe.set_route("List", "Event"));
		// The report is for Desk Users; OneIntake's deadlines are read in it.
		if (frappe.user.has_role(["Desk User", "Workspace Administrator"]))
			link(__("Deadlines"), "alarm-clock", () => frappe.set_route("query-report", "Deadlines"));
		// Only where the workspace allows calendar links (Workspace › General).
		if (!this.about && frappe.boot.one_calendar_links) link(__("Subscribe"), "rss", () => this.subscribe());
		const setup = [
			["Google Calendar", __("Google Calendar")],
			["Calendar Feed", __("Calendar Links")],
		].filter(([doctype]) => frappe.model.can_read(doctype));
		if (!setup.length) return;
		const $setup = frappe.ui.button({ label: __("Setup"), icon: "settings", icon_right: "chevron-down", variant: "ghost", css_class: "one-calendar-link" }).appendTo($foot);
		new frappe.ui.Dropdown({
			trigger: $setup,
			side: "top",
			options: setup.map(([doctype, label]) => ({ label, onclick: () => frappe.set_route("List", doctype) })),
		});
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
		this.calendar = new frappe.FullCalendar(this.$grid[0], {
			plugins: frappe.FullCalendar.Plugins,
			initialView: this.saved.view || "timeGridWeek",
			// A notice about an event opens the calendar on its day.
			initialDate: frappe.utils.get_query_params().date || undefined,
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
			eventSources: [
				{ events: (info, done, failed) => this.entries(info).then(done, failed) },
				// The workspace's days off, shaded behind everything else.
				{ events: (info, done, failed) => this.days_off(info).then(done, failed), display: "background" },
			],
			select: (info) => this.new_event(info),
			eventClick: (info) => this.open(info),
			eventDrop: (info) => this.move(info),
			eventResize: (info) => this.move(info),
			eventDidMount: (info) => {
				// The whole title on hover, since a short event cuts it off.
				const said = info.event.extendedProps.description;
				info.el.title = said ? `${info.event.title}\n${said}` : info.event.title;
				// An event opens a card beside it (frappe.ui.Popover); anything
				// else opens its record (`open`).
				if (info.event.extendedProps.doctype === "Event" && info.event.display !== "background") {
					new frappe.ui.Popover({
						trigger: info.el,
						side: "right",
						align: "start",
						css_class: "one-calendar-card",
						// The time is the one clicked: a repeat's, not its first.
						content: () => this.card(info.event.extendedProps.name, info.event),
					});
				}
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
		this.listen();
	}

	// Anything on a layer that changes elsewhere is drawn again: frappe's own
	// list_update, for each doctype a layer reads, a moment after the last.
	listen() {
		const doctypes = new Set(["Event", ...this.layers.map((one) => one.doctype).filter(Boolean)]);
		doctypes.forEach((doctype) => frappe.realtime.doctype_subscribe(doctype));
		const again = frappe.utils.debounce(() => this.refetch(), 800);
		frappe.realtime.on("list_update", (data) => {
			if (data && doctypes.has(data.doctype) && this.$grid.is(":visible")) again();
		});
	}

	// Holidays and weekly days off, from the list in force on each day.
	async days_off(info) {
		const last = moment(info.end).subtract(1, "day");
		const rows = await frappe.xcall("onedesk.one_calendar.layers.days_off", {
			start: moment(info.start).format("YYYY-MM-DD"),
			end: last.format("YYYY-MM-DD"),
		});
		return (rows || []).map((one) => ({
			start: one.date,
			allDay: true,
			display: "background",
			title: one.weekly ? "" : one.title,
			backgroundColor: one.weekly ? "var(--surface-gray-2)" : "var(--surface-red-1)",
			classNames: [one.weekly ? "one-calendar-weekly-off" : "one-calendar-holiday"],
		}));
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
		this.$toolbar.append(
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
		const $side = this.$layers.empty();
		for (const group of ["Mine", "Workspace"]) {
			const mine = this.layers.filter((one) => one.group === group);
			if (!mine.length) continue;
			$side.append(`<div class="one-calendar-group">${__(group)}</div>`);
			for (const one of mine) {
				// Each switch is frappe's Check control, with the layer's colour
				// beside its label.
				const $row = $(`<div class="one-calendar-layer"></div>`).appendTo($side);
				const control = frappe.ui.form.make_control({
					df: { fieldtype: "Check", fieldname: one.key, label: one.label },
					parent: $row,
					render_input: true,
				});
				control.set_input(this.off().includes(one.key) ? 0 : 1);
				control.$wrapper
					.find(".label-area")
					.before(`<span class="one-calendar-dot" style="background: var(--ink-${one.color}-7)"></span>`);
				control.$input.on("change", (e) => {
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
		// An event's card is its popover's; the click that opens it ends here.
		if (one.doctype === "Event") return;
		frappe.set_route("Form", one.doctype, one.name);
	}

	// The card on an event: when, where, who, what it says, a Join link, and
	// Open and Delete for whoever may. Filled once the event is read.
	card(name, at) {
		const $card = $(`<div class="one-calendar-card-body">${onedesk.shell.quiet(__("Loading…"))}</div>`);
		frappe.xcall("onedesk.one_calendar.events.card", { name }).then((one) => {
			const esc = frappe.utils.escape_html;
			const day = (when) => frappe.datetime.str_to_user(when, false, true).split(" ")[0];
			const time = (when) => moment(when).format(frappe.boot.sysdefaults.time_format === "HH:mm" ? "HH:mm" : "h:mm a");
			const starts = at && at.start ? moment(at.start).format("YYYY-MM-DD HH:mm:ss") : one.starts_on;
			const ends = at && at.end && !one.all_day ? moment(at.end).format("YYYY-MM-DD HH:mm:ss") : one.ends_on;
			let when = day(starts);
			if (!one.all_day) when += ` · ${time(starts)}${ends ? ` – ${time(ends)}` : ""}`;
			else if (one.ends_on && day(one.ends_on) !== day(one.starts_on)) when += ` – ${day(one.ends_on)}`;
			const rows = [
				[ "clock", esc(when) + (one.repeats ? ` · ${esc(__(one.repeats))}` : "") ],
				one.location ? ["map-pin", esc(one.location)] : null,
				["user", esc(__("By {0}", [one.owner]))],
				one.people.length
					? ["users", one.people.map((p) => esc(p.name) + (p.answer ? ` <span class="text-ink-gray-5">(${esc(__(p.answer))})</span>` : "")).join(", ")]
					: null,
			].filter(Boolean);
			$card.html(`
				<div class="one-calendar-card-title">${esc(one.subject)}</div>
				${rows.map(([icon, html]) => `<div class="one-calendar-card-row">${frappe.utils.icon(icon, "sm")}<span>${html}</span></div>`).join("")}
				${one.description ? `<div class="one-calendar-card-said">${one.description}</div>` : ""}
				<div class="one-calendar-card-foot"></div>`);
			const $foot = $card.find(".one-calendar-card-foot");
			if (one.join) frappe.ui.button({ label: __("Join"), icon: "video", variant: "solid", onclick: () => window.open(one.join, "_blank", "noopener") }).appendTo($foot);
			if (one.can_open) frappe.ui.button({ label: __("Open"), icon: "external-link", onclick: () => frappe.set_route("Form", "Event", one.name) }).appendTo($foot);
			else if (one.about) frappe.ui.button({ label: __("Open {0}", [__(one.about[0])]), icon: "external-link", onclick: () => frappe.set_route("Form", one.about[0], one.about[1]) }).appendTo($foot);
			if (one.can_edit)
				frappe.ui
					.button({
						label: __("Delete"),
						icon: "trash-2",
						variant: "ghost",
						theme: "red",
						onclick: () =>
							frappe.confirm(__("Delete {0}? Everybody on it is told it is cancelled.", [`<b>${esc(one.subject)}</b>`]), async () => {
								await frappe.xcall("frappe.client.delete", { doctype: "Event", name: one.name });
								$(document.body).trigger("click");
								this.refetch();
							}),
					})
					.appendTo($foot);
		});
		return $card[0];
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
				// frappe's own sections and columns: what an event needs on top,
				// who it is with beside it, and the rest folded under More.
				{ fieldtype: "Data", fieldname: "subject", label: __("Subject"), reqd: 1 },
				{ fieldtype: "Section Break" },
				{ fieldtype: "Datetime", fieldname: "starts_on", label: __("Starts On"), reqd: 1, default: start.format("YYYY-MM-DD HH:mm:ss") },
				{ fieldtype: "Check", fieldname: "all_day", label: __("All Day"), default: all_day ? 1 : 0 },
				{ fieldtype: "Column Break" },
				{ fieldtype: "Datetime", fieldname: "ends_on", label: __("Ends On"), default: end.format("YYYY-MM-DD HH:mm:ss") },
				{ fieldtype: "Section Break" },
				{ fieldtype: "Data", fieldname: "location", label: __("Location") },
				{ fieldtype: "Column Break" },
				{
					// People in the workspace, by name; frappe's own pills.
					fieldtype: "MultiSelectPills",
					fieldname: "team",
					label: __("Invite"),
					get_data: (txt) =>
						frappe
							.xcall("frappe.desk.search.search_link", {
								doctype: "User",
								txt: txt || "",
								filters: { user_type: "System User", enabled: 1 },
								page_length: 10,
							})
							.then((found) => (found || []).map((one) => ({ value: one.value, description: one.description }))),
				},
				{ fieldtype: "Section Break" },
				{
					fieldtype: "Data",
					fieldname: "guests",
					label: __("Guests"),
					description: __("Email addresses of people outside the workspace. Each is mailed an invitation for their own calendar."),
				},
				{ fieldtype: "Section Break", label: __("More"), collapsible: 1 },
				{ fieldtype: "Small Text", fieldname: "description", label: __("Description") },
				{
					fieldtype: "Check",
					fieldname: "public",
					label: __("On Everybody's Calendar"),
					hidden: may_publish ? 0 : 1,
				},
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_calendar.events.make", {
					values: {
						...values,
						// Made on a record's calendar, it is about that record.
						...(this.about ? { reference_doctype: this.about.doctype, reference_docname: this.about.name } : {}),
					},
				});
				dialog.hide();
				this.calendar.unselect();
				this.refetch();
			},
		});
		dialog.show();
	}

	// The link as Settings › Calendar draws it (public/js/calendar_link.js).
	subscribe() {
		return onedesk.calendar_link.dialog();
	}
};
