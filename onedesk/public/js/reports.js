frappe.provide("onedesk.reports");

const ALSO = ["include_company_descendants", "show_aggregate_value_from_subsidiary_companies"];

const PAID = ["HR", "Payroll", "One HR"];

onedesk.reports.one_company = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_company) return;
	QueryReport.prototype.__one_company = true;

	const theirs = QueryReport.prototype.setup_filters;
	QueryReport.prototype.setup_filters = function () {
		theirs.call(this);
		const paid = PAID.includes((this.report_doc || {}).module);
		(this.filters || []).forEach((filter) => hide_company(filter, paid));
	};
};

function hide_company(filter, paid) {
	const df = filter.df || {};
	const company = df.fieldtype === "Link" && df.options === "Company";
	const currency = paid && df.fieldtype === "Link" && df.options === "Currency";
	if (!company && !currency && !ALSO.includes(df.fieldname)) return;

	if (!filter.get_value()) {
		if (company) filter.set_input(frappe.defaults.get_user_default("Company"));
		if (currency) filter.set_input(frappe.defaults.get_default("currency"));
	}
	df.hidden = 1;
	filter.$wrapper.addClass("one-gone");
}

onedesk.reports.called_what_the_rail_called_it = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_titles) return;
	QueryReport.prototype.__one_titles = true;

	const theirs = QueryReport.prototype.load_report;
	QueryReport.prototype.load_report = function (...args) {
		const result = theirs.apply(this, args);
		const ours = ((frappe.boot.one_titles || {}).Report || {})[this.report_name];
		if (ours) this.page_title = __(ours);
		return result;
	};
};

onedesk.reports.one_name = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_name) return;
	QueryReport.prototype.__one_name = true;

	const theirs = QueryReport.prototype.prepare_columns;
	QueryReport.prototype.prepare_columns = function (columns) {
		const ready = theirs.call(this, columns);
		const linked = ready.some((c) => c.fieldtype === "Link" && c.options === "Employee");
		for (const c of ready) {
			if (c.fieldname === "company" || (linked && c.fieldname === "employee_name")) c.hidden = 1;
		}
		return ready;
	};
};

const MONTHLY = ["Salary Register", "Income Tax Deductions"];

onedesk.reports.a_payroll_month = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_month) return;
	QueryReport.prototype.__one_month = true;

	const theirs = QueryReport.prototype.setup_filters;
	QueryReport.prototype.setup_filters = function () {
		theirs.call(this);
		if (!MONTHLY.includes(this.report_name)) return;
		const report = this;
		frappe.db
			.get_list("Salary Slip", {
				filters: { docstatus: 1 },
				fields: ["start_date", "end_date"],
				order_by: "end_date desc",
				limit: 1,
			})
			.then((found) => {
				if (!found.length) return;
				const on = frappe.datetime.str_to_obj(found[0].end_date);
				const run = {
					from_date: found[0].start_date,
					to_date: found[0].end_date,
					month: String(on.getMonth() + 1),
					year: String(on.getFullYear()),
				};
				(report.filters || []).forEach((filter) => {
					const when = run[filter.df.fieldname];
					if (when) filter.set_input(when);
				});
				report.refresh();
			});
	};
};

onedesk.reports.dashboards_too = () => {
	const Page = frappe.ui.Page;
	if (!Page || Page.prototype.__one_titles) return;
	Page.prototype.__one_titles = true;

	const theirs = Page.prototype.set_breadcrumbs;
	Page.prototype.set_breadcrumbs = function (items) {
		const route = frappe.get_route();
		const last = (items || [])[items?.length - 1];
		const ours = route[0] === "dashboard-view" && ((frappe.boot.one_titles || {}).Dashboard || {})[last?.label];
		if (ours) items = [...items.slice(0, -1), { ...last, label: __(ours) }];
		return theirs.call(this, items);
	};
};

const PERIODS = {
	"Payroll Period": ["start_date", "end_date"],
	"Fiscal Year": ["year_start_date", "year_end_date"],
};

onedesk.reports.the_period = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_period) return;
	QueryReport.prototype.__one_period = true;

	const theirs = QueryReport.prototype.setup_filters;
	QueryReport.prototype.setup_filters = function () {
		theirs.call(this);
		const report = this;
		const today = frappe.datetime.get_today();

		Object.entries(PERIODS).forEach(([doctype, [starts, ends]]) => {
			const wants = (report.filters || []).filter(
				(filter) =>
					filter.df.fieldtype === "Link" &&
					filter.df.options === doctype &&
					!filter.get_value()
			);
			if (!wants.length) return;

			frappe.db
				.get_list(doctype, {
					filters: { [starts]: ["<=", today] },
					fields: ["name", ends],
					order_by: `${starts} desc`,
					limit: 5,
				})
				.then((found) => {
					const now = found.find((period) => period[ends] >= today) || found[0];
					if (!now) return;
					wants.forEach((filter) => filter.set_input(now.name));
					report.refresh();
				});
		});
	};
};

const CHOSEN = { "Employee Analytics": { parameter: "Department" } };

const KINDS = { "Address And Contacts": { party_type: ["Customer", "Lead", "Supplier", "Sales Partner"] } };

const STARTS = { "Delayed Order Report": { based_on: "Delivery Note" } };

onedesk.reports.a_choice_is_made = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_choice) return;
	QueryReport.prototype.__one_choice = true;

	const theirs = QueryReport.prototype.setup_filters;
	QueryReport.prototype.setup_filters = function () {
		const kinds = KINDS[this.report_name] || {};
		const starts = STARTS[this.report_name] || {};
		for (const df of this.report_settings?.filters || []) {
			if (starts[df.fieldname]) df.default = starts[df.fieldname];
			if (!kinds[df.fieldname]) continue;
			Object.assign(df, {
				fieldtype: "Select",
				options: kinds[df.fieldname].filter((kind) => frappe.model.can_read(kind)),
				get_query: null,
			});
		}
		theirs.call(this);
		const named = CHOSEN[this.report_name] || {};
		(this.filters || []).forEach((filter) => {
			const df = filter.df || {};
			if (df.fieldtype !== "Select" || !df.reqd || filter.get_value()) return;
			const first = (df.options || []).find((option) =>
				typeof option === "string" ? option : option && option.value
			);
			const answer = named[df.fieldname] || (typeof first === "string" ? first : first && first.value);
			if (answer) filter.set_value(answer);
		});
	};
};

const WHOLE_YEAR = ["Employee Exits"];

onedesk.reports.who_is_leaving = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_year) return;
	QueryReport.prototype.__one_year = true;

	const theirs = QueryReport.prototype.setup_filters;
	QueryReport.prototype.setup_filters = function () {
		theirs.call(this);
		if (!WHOLE_YEAR.includes(this.report_name)) return;
		const today = frappe.datetime.nowdate();
		const was = { from_date: frappe.datetime.add_months(today, -12), to_date: today };
		(this.filters || []).forEach((filter) => {
			const fieldname = (filter.df || {}).fieldname;
			if (!(fieldname in was) || filter.get_value() !== was[fieldname]) return;
			filter.set_value(
				fieldname === "from_date" ? frappe.datetime.year_start() : frappe.datetime.year_end()
			);
		});
	};
};

const EMPTY = { "Stock and Account Value Comparison": () => __("Stock and the books agree") };

onedesk.reports.good_news = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_empty) return;
	QueryReport.prototype.__one_empty = true;

	const theirs = QueryReport.prototype.get_no_result_message;
	QueryReport.prototype.get_no_result_message = function () {
		const title = EMPTY[this.report_name];
		if (!title) return theirs.call(this);
		return frappe.ui.empty_state({ icon: "check", title: title() })[0].outerHTML;
	};
};

onedesk.reports.lists_too = () => {
	const BaseList = frappe.views && frappe.views.BaseList;
	const ours = (doctype) => ((frappe.boot.one_titles || {}).DocType || {})[doctype];
	const crumb = (doctype) => ((frappe.boot.one_titles || {}).Crumb || {})[doctype];
	if (BaseList && !BaseList.prototype.__one_titles) {
		BaseList.prototype.__one_titles = true;
		const theirs = BaseList.prototype.get_breadcrumbs;
		BaseList.prototype.get_breadcrumbs = function () {
			const label = ours(this.doctype) || crumb(this.doctype);
			if (label && !frappe.router.doctype_layout) this.page_title = __(label);
			return theirs.call(this);
		};
	}
	const TreeView = frappe.views && frappe.views.TreeView;
	if (TreeView && !TreeView.prototype.__one_titles) {
		TreeView.prototype.__one_titles = true;
		const theirs = TreeView.prototype.set_title;
		TreeView.prototype.set_title = function () {
			const label = !this.opts.title && crumb(this.doctype);
			return label ? this.page.set_title(__(label)) : theirs.call(this);
		};
	}
	const Dashboard = frappe.ui.form && frappe.ui.form.Dashboard;
	if (Dashboard && !Dashboard.prototype.__one_titles) {
		Dashboard.prototype.__one_titles = true;
		const theirs = Dashboard.prototype.render_links;
		Dashboard.prototype.render_links = function () {
			const out = theirs.apply(this, arguments);
			this.transactions_area.find(".document-link[data-doctype]").each(function () {
				const label = ours($(this).attr("data-doctype"));
				if (label) $(this).find(".badge-link").text(__(label));
			});
			return out;
		};
	}
};

onedesk.reports.show_in = async (kind, name) => {
	const said = await frappe.xcall("onedesk.one_studio.reports.where", { kind, name });
	const dialog = new frappe.ui.Dialog({
		title: __("Show In"),
		fields: [
			{
				fieldname: "module",
				fieldtype: "Select",
				label: __("App"),
				options: [{ value: "", label: __("Nowhere") }, ...said.places.map((one) => ({ value: one.module, label: one.label }))],
				default: said.module || "",
				description: __("{0} appears in the app's sidebar under {1}.", [name, kind === "Report" ? __("Saved Reports") : __("Dashboards")]),
			},
			{
				fieldname: "everybody",
				fieldtype: "Select",
				label: __("Visible To"),
				options: [
					{ value: "0", label: __("Only me") },
					{ value: "1", label: __("All Users") },
				],
				default: String(said.everybody),
				hidden: !said.administers,
				depends_on: "eval:doc.module",
			},
		],
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			await frappe.xcall("onedesk.one_studio.reports.place", {
				kind,
				name,
				module: values.module || null,
				everybody: cint(values.everybody),
			});
			dialog.hide();
			frappe.show_alert({ message: __("Saved"), indicator: "green" });
		},
	});
	dialog.show();
};

onedesk.reports.shown_in = () => {
	const ReportView = frappe.views && frappe.views.ReportView;
	if (ReportView && !ReportView.prototype.__one_show_in) {
		ReportView.prototype.__one_show_in = true;
		const theirs = ReportView.prototype.report_menu_items;
		ReportView.prototype.report_menu_items = function () {
			const items = theirs.call(this);
			if (this.report_name) items.push({ label: __("Show In…"), action: () => onedesk.reports.show_in("Report", this.report_name) });
			return items;
		};
	}
	frappe.router.on("change", () => {
		const route = frappe.get_route();
		if (route[0] !== "dashboard-view" || !frappe.user.has_role("Workspace Administrator")) return;
		const wrap = (tries) => {
			const shown = frappe.dashboard;
			if (!shown || !shown.page) return tries && setTimeout(() => wrap(tries - 1), 200);
			const proto = Object.getPrototypeOf(shown);
			if (proto.__one_show_in) return;
			proto.__one_show_in = true;
			const add = (one) => one.page.add_menu_item(__("Show In…"), () => onedesk.reports.show_in("Dashboard", one.dashboard_name));
			const theirs = proto.set_dropdown;
			proto.set_dropdown = function () {
				theirs.call(this);
				add(this);
			};
			add(shown);
		};
		wrap(25);
	});
	$(document).on("app_ready", () =>
		frappe.realtime.on("one_report_placed", ({ report }) =>
			frappe.show_alert(
				{
					message: __("Saved under Saved Reports in this app's sidebar."),
					body: `<a class="one-link" data-action="show_in">${frappe.utils.escape_html(__("Show In…"))}</a>`,
					indicator: "green",
				},
				10,
				{ show_in: () => onedesk.reports.show_in("Report", report) }
			)
		)
	);
};

frappe.ui.form.on("Dashboard", {
	refresh(frm) {
		if (!frm.is_new() && !frm.doc.is_standard && frappe.user.has_role("Workspace Administrator"))
			frm.add_custom_button(__("Show In…"), () => onedesk.reports.show_in("Dashboard", frm.doc.name));
	},
});

onedesk.reports.one_period_bars = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_bars) return;
	QueryReport.prototype.__one_bars = true;
	const theirs = QueryReport.prototype.get_chart_options;
	QueryReport.prototype.get_chart_options = function (data) {
		const options = theirs.call(this, data);
		if (options && options.type === "line" && options.data.labels.length === 1) options.type = "bar";
		if (options && ["Accounts Receivable", "Accounts Payable"].includes(this.report_name))
			options.data.labels = options.data.labels.map((label) => (label === "<0" ? __("Not Yet Due") : label));
		return options;
	};
};

const COLUMNS = {
	"Accounts Receivable": {
		dropped: ["party_type", "customer_primary_contact"],
		first: ["posting_date", "party", "voucher_no", "due_date", "invoiced", "paid", "credit_note", "outstanding", "age"],
	},
	"Accounts Payable": {
		dropped: ["party_type"],
		first: ["posting_date", "party", "voucher_no", "due_date", "invoiced", "paid", "credit_note", "outstanding", "age"],
	},
	"Gross Profit": {
		first: ["sales_invoice", "customer", "posting_date", "qty", "selling_amount", "buying_amount", "gross_profit", "gross_profit_%"],
	},
};

onedesk.reports.columns_that_say_something = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_columns) return;
	QueryReport.prototype.__one_columns = true;
	const theirs = QueryReport.prototype.prepare_report_data;
	QueryReport.prototype.prepare_report_data = function (data) {
		const rows = ((data && data.result) || []).filter((row) => row && typeof row === "object");
		const records = rows.filter((row) => !Array.isArray(row));
		const described = (data && data.columns || []).every((column) => column && typeof column === "object");
		if (records.length && described) {
			const said = COLUMNS[this.report_name] || {};
			const all = data.columns || [];
			const empty = (column) => {
				const name = column.fieldname;
				return name && records.every((row) => row[name] === null || row[name] === undefined || row[name] === "");
			};
			let kept = all.map((column, at) => at).filter((at) => at === 0 || !((said.dropped || []).includes(all[at].fieldname) || empty(all[at])));
			if (said.first) {
				const rank = (at) => {
					const found = said.first.indexOf(all[at].fieldname);
					return found === -1 ? said.first.length : found;
				};
				kept = kept.sort((a, b) => rank(a) - rank(b) || a - b);
			}
			const result = (data.result || []).map((row) => (Array.isArray(row) ? kept.map((at) => row[at]) : row));
			data = { ...data, columns: kept.map((at) => all[at]), result };
		}
		return theirs.call(this, data);
	};
};

onedesk.reports.books_kept = () => {
	const QueryReport = frappe.views && frappe.views.QueryReport;
	if (!QueryReport || QueryReport.prototype.__one_books) return;
	QueryReport.prototype.__one_books = true;
	let kept = null;
	const theirs = QueryReport.prototype.setup_filters;
	QueryReport.prototype.setup_filters = function () {
		const out = theirs.apply(this, arguments);
		const filters = (this.filters || []).filter(
			(filter) => (filter.df.fieldtype === "Link" && filter.df.options === "Finance Book") || filter.df.fieldname === "include_default_book_entries"
		);
		if (!filters.length) return out;
		kept = kept || frappe.db.count("Finance Book");
		kept.then((count) => {
			if (count) return;
			filters.forEach((filter) => {
				filter.df.hidden = 1;
				filter.$wrapper && filter.$wrapper.hide();
			});
		});
		return out;
	};
};

onedesk.reports.wrap = () => {
	onedesk.reports.one_company();
	onedesk.reports.one_name();
	onedesk.reports.a_payroll_month();
	onedesk.reports.the_period();
	onedesk.reports.called_what_the_rail_called_it();
	onedesk.reports.dashboards_too();
	onedesk.reports.lists_too();
	onedesk.reports.a_choice_is_made();
	onedesk.reports.who_is_leaving();
	onedesk.reports.good_news();
	onedesk.reports.one_period_bars();
	onedesk.reports.columns_that_say_something();
	onedesk.reports.books_kept();
};
onedesk.reports.wrap();

frappe.after_ajax(() => {
	onedesk.reports.shown_in();
	onedesk.reports.wrap();
});
