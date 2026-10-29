// OneHR's ControlCenter (docs/ONE.md): Holidays, the lists of public
// holidays and weekly days off, for the workspace's administrators
// (one_hr/control.py, one_hr/holidays.py), and OneHR's Lists (lists.js).
// A holiday list other than the one in force opens as the record the tab is on.
frappe.provide("onedesk.hr_control");

onedesk.HRSection = class HRSection extends onedesk.CenterSection {
	static API = "onedesk.one_hr.control.";
	static HERE = "onehr";
	static LABEL = "ControlCenter";

	draw_holidays(data) {
		const esc = frappe.utils.escape_html;
		const open_list = (name) => this.open("holidays", { record: name === data.now ? null : name });
		const use_another = () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Use Another List"),
				fields: [
					{ fieldname: "holiday_list", fieldtype: "Link", options: "Holiday List", label: __("Holiday List"), reqd: 1 },
					{
						fieldname: "said",
						fieldtype: "HTML",
						options: `<div class="one-shell-quiet">${esc(
							__("Applies to everyone from today, or from its start date. Used for leave, attendance, check-ins, the calendar and deadlines.")
						)}</div>`,
					},
				],
				primary_action_label: __("Use List"),
				primary_action: async (values) => {
					await frappe.xcall("onedesk.one_hr.holidays.use", { holiday_list: values.holiday_list });
					dialog.hide();
					this.refresh({ fresh: true });
				},
			});
			dialog.show();
		};
		const next_year = async () => {
			const name = await frappe.xcall("onedesk.one_hr.holidays.next_year");
			frappe.show_alert({ message: __("{0} created", [name]), indicator: "green" });
			open_list(name);
		};
		if (data.empty) {
			this.$content.append(
				onedesk.shell.section(__("Holidays"), onedesk.shell.empty(__("No holiday list")))
			);
			this.page.add_inner_button(__("Use Another List"), use_another);
			return;
		}
		const list = data.list;
		const day = (value) => frappe.datetime.str_to_user(value);
		if (list.in_force && !data.next && list.days_left <= 90) {
			const $make = $(onedesk.shell.button(__("Create Next Year's List"), {}, "ghost")).on("click", next_year);
			this.$content.append(
				$(
					frappe.ui.alert({
						title: __("Ends {0}, in {1} days", [day(list.to_date), list.days_left]),
						description: __("After that, every day counts as a working day for leave and attendance, until another list starts."),
						theme: "yellow",
						footer: $make,
					})
				).addClass("os-holiday-alert")
			);
		} else if (!list.in_force) {
			const $back = $(onedesk.shell.button(__("Back to {0}", [data.now]), {}, "ghost")).on("click", () => open_list(data.now));
			this.$content.append(
				$(
					frappe.ui.alert({
						title: __("{0} starts on {1}", [list.name, day(list.from_date)]),
						description: __("Until then, {0} applies.", [data.now]),
						theme: "blue",
						footer: $back,
					})
				).addClass("os-holiday-alert")
			);
		}
		const fact = (value, label, href) =>
			`<${href ? `a href="${esc(href)}"` : "div"} class="os-intake-fact"><span class="os-intake-number">${esc(String(value))}</span><span class="one-shell-quiet">${esc(label)}</span></${href ? "a" : "div"}>`;
		const coming = (data.coming || [])[0];
		const facts = `<div class="os-intake-facts">${[
			fact(list.public, __("Public Holidays")),
			fact(list.days_off, __("Weekly Days Off")),
			coming ? fact(day(coming.date), coming.what) : fact("–", __("No More Holidays This Year")),
			fact(day(list.to_date), list.days_left >= 0 ? __("Last Day, in {0} days", [list.days_left]) : __("Ended")),
			...(data.elsewhere ? [fact(data.elsewhere, __("People on Other Lists"), "/desk/holiday-list-assignment?applicable_for=Employee&docstatus=1")] : []),
		].join("")}</div>`;
		this.$content.append(
			onedesk.shell.section(list.name, facts, __("{0} to {1}", [day(list.from_date), day(list.to_date)]))
		);
		this.form(data, {
			rows: [
				{ heading: __("Days Off") },
				{ stack: ["weekly_offs"] },
				{ heading: __("Public Holidays") },
				["country", "subdivision"],
				{ html: onedesk.shell.button(__("Add Public Holidays"), { "data-local": "1" }, "subtle", "plus") },
				{ stack: ["holidays"] },
			],
		});
		const country = this.group.get_field("country");
		const region = this.group.get_field("subdivision");
		const regions = async () => {
			const code = this.group.get_value("country");
			region.set_data(code ? await frappe.xcall("onedesk.one_hr.holidays.subdivisions", { country: code }) : []);
		};
		country.df.onchange = regions;
		this.$content.find("[data-local]").on("click", async () => {
			const code = this.group.get_value("country");
			if (!code) return frappe.msgprint(__("Choose the country first."));
			const found = await frappe.xcall("onedesk.one_hr.holidays.country_holidays", {
				country: code,
				subdivision: this.group.get_value("subdivision") || null,
				from_date: list.from_date,
				to_date: list.to_date,
			});
			const table = this.group.get_field("holidays");
			const held = new Set((table.df.data || []).map((one) => one.holiday_date));
			const added = found.filter((one) => !held.has(one.holiday_date));
			table.df.data = [...(table.df.data || []), ...added].sort((a, b) => (a.holiday_date < b.holiday_date ? -1 : 1));
			table.df.data.forEach((one, at) => (one.idx = at + 1));
			table.grid.refresh();
			this.check();
			frappe.show_alert({ message: added.length ? __("{0} holidays added. Save to keep them.", [added.length]) : __("All holidays are already in the list."), indicator: "blue" });
		});
		if (list.in_force && data.next) this.page.add_inner_button(__("Next Year's List"), () => open_list(data.next));
		else if (list.in_force) this.page.add_inner_button(__("Create Next Year's List"), next_year);
		this.page.add_inner_button(__("Use Another List"), use_another);
	}
};

// Holidays are the administrators'; everybody else has what every module's
// settings find (its lists, notifications and agreements).
onedesk.hr_control.open = ({ at = null, record = null } = {}) => {
	const holidays = onedesk.center_section.tab(onedesk.HRSection, {
		id: "holidays",
		label: __("Holidays"),
		icon: "calendar-days",
		about: __("The public holidays and weekly days off leave and attendance count around."),
		record: at === "holidays" ? record : null,
	});
	const dialog = onedesk.module_settings.open({
		module: "OneHR",
		tabs: frappe.boot.one_administers ? [{ group: null, items: [holidays] }] : [],
		default_tab: at,
	});
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneHR = onedesk.hr_control.open;

// Its foot: Settings, the tour, Help and the version at the foot of its rail,
// drawn by the window under whichever of its screens is open (module_foot).
$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.window.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== "OneHR") return;
		win.module_foot({ module: "OneHR", settings: () => onedesk.hr_control.open() });
		onedesk.window.nav.place();
	}, 0)
);
