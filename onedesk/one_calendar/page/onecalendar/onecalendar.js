
frappe.pages["onecalendar"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, onedesk.names.of("one_calendar"), { mark: "onecalendar", fit: true });
	wrapper.onecalendar = new onedesk.OneCalendar(page);
};

frappe.pages["onecalendar"].on_page_show = (wrapper) => {
	wrapper.onecalendar && wrapper.onecalendar.show();
};

frappe.provide("onedesk");

onedesk.OneCalendar = class OneCalendar {
	// The rail stays OneCalendar's: Calendar, Event, Deadlines and Setup are
	// its rows, and the layers are a section of the nav pane under them
	// (window.tree). The days shown head the page with New Event beside them
	// and the views at the far end (look.js heading); Today and moving
	// through the days join the address row.
	constructor(page) {
		this.page = page;
		this.about = this.narrowed();
		this.$grid = $(`<div class="one-calendar one-calendar-grid" data-tour="onecalendar-grid"></div>`).appendTo(page.$shell);
		onedesk.shell.fit(this.$grid);
		frappe.require("calendar.bundle.js", () => this.start());
	}

	save() {
		const off = this.saved.off ? { off: this.saved.off.join(",") } : {};
		frappe.model.user_settings.save("Event", "OneCalendar", { view: this.saved.view, ...off });
	}

	narrowed() {
		const { doctype, name } = frappe.utils.get_query_params();
		return doctype && name ? { doctype, name } : null;
	}

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
		if (this.about) {
			const { doctype, name } = this.about;
			const title = (await frappe.utils.fetch_link_title(doctype, name)) || name;
			this.page.set_title(__("Calendar"));
			onedesk.shell.trail(title, `/desk/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}`, __("Calendar"));
		} else {
			this.page.set_title(onedesk.names.of("one_calendar"));
			onedesk.shell.name(onedesk.names.of("one_calendar"));
		}
	}

	off() {
		return this.about ? this.off_here || [] : this.saved.off;
	}

	async start() {
		const settings = await frappe.model.user_settings.get("Event");
		const kept = (settings && settings.OneCalendar) || {};
		this.saved = { view: kept.view, off: typeof kept.off === "string" ? kept.off.split(",").filter(Boolean) : null };
		await this.read_layers();
		const kept_view = this.saved.view || "timeGridWeek";
		this.first_view = frappe.is_mobile() && kept_view === "timeGridWeek" ? "timeGridDay" : kept_view;
		this.draw_toolbar();
		this.calendar = new frappe.FullCalendar(this.$grid[0], {
			plugins: frappe.FullCalendar.Plugins,
			initialView: this.first_view,
			initialDate: frappe.utils.get_query_params().date || undefined,
			headerToolbar: false,
			allDayText: __("All Day"),
			noEventsText: __("No events"),
			firstDay: frappe.datetime.get_first_day_of_the_week_index(),
			locale: `${frappe.boot.lang}-u-nu-latn`,
			direction: frappe.utils.is_rtl() ? "rtl" : "ltr",
			height: "100%",
			nowIndicator: true,
			selectable: true,
			selectMirror: true,
			dayMaxEvents: true,
			eventDisplay: "block",
			eventMinHeight: 22,
			scrollTime: "08:00:00",
			eventSources: [
				{ events: (info, done, failed) => this.entries(info).then(done, failed) },
				{ events: (info, done, failed) => this.days_off(info).then(done, failed), display: "background" },
			],
			select: (info) => this.new_event(info),
			eventClick: (info) => this.open(info),
			eventDrop: (info) => this.move(info),
			eventResize: (info) => this.move(info),
			eventDidMount: (info) => {
				const said = info.event.extendedProps.description;
				info.el.title = said ? `${info.event.title}\n${said}` : info.event.title;
				if (info.event.extendedProps.doctype === "Event" && info.event.display !== "background") {
					new frappe.ui.Popover({
						trigger: info.el,
						side: "right",
						align: "start",
						css_class: "one-calendar-card",
						content: () => this.card(info.event.extendedProps.name, info.event),
					});
				}
			},
			datesSet: (info) => {
				this.head(info.view.title, info.view.type);
				const now = new Date();
				this.$today.prop("disabled", info.view.activeStart <= now && now < info.view.activeEnd);
				if (this.drawn && this.saved.view !== info.view.type) {
					this.saved.view = info.view.type;
					this.save();
				}
			},
		});
		this.calendar.render();
		this.drawn = true;
		this.listen();
	}

	listen() {
		const doctypes = new Set(["Event", ...this.layers.map((one) => one.doctype).filter(Boolean)]);
		doctypes.forEach((doctype) => frappe.realtime.doctype_subscribe(doctype));
		const again = frappe.utils.debounce(() => this.refetch(), 800);
		frappe.realtime.on("list_update", (data) => {
			if (data && doctypes.has(data.doctype) && this.$grid.is(":visible")) again();
		});
	}

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

	draw_toolbar() {
		this.$today = frappe.ui.button({ label: __("Today"), onclick: () => this.calendar.today() });
		const moves = $(`<span class="one-calendar-moves" data-tour="onecalendar-moves"></span>`).append(
			this.$today,
			frappe.ui.button({ icon: "chevron-left", variant: "ghost", title: __("Previous"), onclick: () => this.calendar.prev() }),
			frappe.ui.button({ icon: "chevron-right", variant: "ghost", title: __("Next"), onclick: () => this.calendar.next() })
		);
		this.page.interface.view({ commands: moves });
		this.head(__("Calendar"), this.first_view);
	}

	head(title, view) {
		onedesk.interface.heading(this.page.interface, {
			title,
			icon: "calendar",
			primary: { label: __("New Event"), click: () => this.new_event() },
			ways: [
				{ value: "dayGridMonth", icon: "calendar", label: __("Month") },
				{ value: "timeGridWeek", icon: "calendar-range", label: __("Week") },
				{ value: "timeGridDay", icon: "calendar-1", label: __("Day") },
				{ value: "listWeek", icon: "list", label: __("List") },
			],
			ways_label: __("Calendar View"),
			way: view,
			pick_way: (one) => this.calendar.changeView(one),
		});
		const $name = $(this.page.main).find(".one-hero-island h1").first();
		$name.attr({ role: "button", tabindex: 0, title: __("Go to Date") }).addClass("one-calendar-jump");
		this.jumper = new frappe.ui.Popover({ trigger: $name, content: () => this.date_jumper(), css_class: "calendar-date-jumper" });
	}

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
		const rows = [];
		for (const [group, label] of [["Mine", __("Mine")], ["Workspace", __("Workspace")]]) {
			const mine = this.layers.filter((one) => one.group === group);
			if (!mine.length) continue;
			rows.push({ id: `group:${group}`, label, section: true });
			for (const one of mine) rows.push({ id: one.key, label: one.label, color: one.color, check: !this.off().includes(one.key) });
		}
		this.page.interface.tree({
			label: __("Calendars"),
			alone: true,
			rows,
			check: (key, on) => {
				const off = this.off().filter((one) => one !== key);
				if (!on) off.push(key);
				if (this.about) {
					this.off_here = off;
				} else {
					this.saved.off = off;
					this.save();
				}
				this.refetch();
			},
		});
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
			backgroundColor: `var(--surface-${one.color}-1)`,
			borderColor: `var(--surface-${one.color}-1)`,
			textColor: `var(--ink-${one.color}-7)`,
			extendedProps: one,
		}));
	}

	open(info) {
		info.jsEvent.preventDefault();
		const one = info.event.extendedProps;
		if (one.doctype === "Event") return;
		frappe.set_route("Form", one.doctype, one.name);
	}

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
							frappe.confirm(__("Delete {0}? Everyone invited is notified that it's cancelled.", [`<b>${esc(one.subject)}</b>`]), async () => {
								await frappe.xcall("frappe.client.delete", { doctype: "Event", name: one.name });
								$(document.body).trigger("click");
								this.refetch();
							}),
					})
					.appendTo($foot);
			onedesk.places &&
				onedesk.places.emit(
					"onecalendar.event",
					{
						name: one.name,
						subject: one.subject,
						starts_on: starts,
						ends_on: ends,
						all_day: !!one.all_day,
						location: one.location || "",
						description: one.description || "",
						people: one.people || [],
						about: one.about || null,
					},
					{
						note: (text, tone) => onedesk.places.note(text, tone).insertBefore($foot),
						action: (label, handler) =>
							frappe.ui.button({ label: String(label || ""), variant: "subtle", onclick: () => handler() }).appendTo($foot),
					}
				);
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
			.then(() => this.refetch(), () => info.revert());
	}

	new_event(info) {
		const all_day = info ? info.allDay : false;
		const start = info ? moment(info.start) : moment().add(1, "hour").startOf("hour");
		let end = info ? moment(info.end) : moment(start).add(1, "hour");
		if (all_day) end = moment(end).subtract(1, "second");
		const may_publish = !!frappe.boot.one_calendar_publish;
		const dialog = new frappe.ui.Dialog({
			title: __("New Event"),
			fields: [
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
					description: __("Email addresses outside the workspace, each sent an invitation."),
				},
				{ fieldtype: "Section Break", label: __("More"), collapsible: 1 },
				{ fieldtype: "Small Text", fieldname: "description", label: __("Description") },
				{
					fieldtype: "Check",
					fieldname: "public",
					label: __("On Everyone's Calendar"),
					hidden: may_publish ? 0 : 1,
				},
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_calendar.events.make", {
					values: {
						...values,
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
};
