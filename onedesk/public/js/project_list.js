// Projects: where each one stands, in one pill. An open project's pill is its
// health (On Track, At Risk, Off Track), since every open project would
// otherwise read "Open"; a finished one says Completed or Cancelled. ERPNext's
// list put "33%" in place of Open once a task was done; how far it has got is
// its own column. The manager reads as a name because every link to a person
// does (`show_title_field_in_link` on User).
//
// A sub-project reads by its own name, then the project it is under, quieter:
// "Handrails · Villa Al Barsha". The column is narrow and its own name is
// what tells two sub-projects apart. A parent on the page is read off the
// page, one that isn't is asked for once.
const ONE_PARENTS = {};
const HEALTH = { "On Track": "green", "At Risk": "orange", "Off Track": "red" };

// The parent's part of the name, quieter. frappe writes the name as text.
function quiet(listview) {
	listview.$result.find(".list-row a.ellipsis[data-name]").each((_, link) => {
		const doc = listview.data.find((one) => one.name === link.dataset.name);
		const up = doc && doc.one_parent && ONE_PARENTS[doc.one_parent];
		if (!up || link.querySelector(".text-muted") || !link.textContent.endsWith(` · ${up}`)) return;
		link.replaceChildren(
			document.createTextNode(link.textContent.slice(0, -(up.length + 3))),
			Object.assign(document.createElement("span"), { className: "text-muted", textContent: ` · ${up}` })
		);
	});
}

// Every view of Projects (List, Report, Kanban, Timeline, the counts and the
// sidebar's groups) leaves out an employee's onboarding or exit checklist
// (one_hr/lifecycle.py). It is asked for with every load but never shown as
// a filter, so the list does not read "Filters 1" on a page nobody narrowed.
// Filtering on the type yourself takes its place.
const BOARDING = ["Project", "project_type", "!=", "Employee Boarding"];
(() => {
	const List = frappe.views.ListView;
	if (!List || List.prototype.one_boarding) return;
	List.prototype.one_boarding = true;
	const args = List.prototype.get_filters_for_args;
	List.prototype.get_filters_for_args = function () {
		const filters = args.call(this);
		if (this.doctype !== "Project" || filters.some((one) => one[1] === "project_type")) return filters;
		return [...filters, BOARDING];
	};
	// The address carries only what somebody chose.
	const search = List.prototype.get_search_params;
	List.prototype.get_search_params = function () {
		const params = search.call(this);
		if (this.doctype === "Project" && !this.filter_area?.get().some((one) => one[1] === "project_type")) {
			params.delete("project_type");
		}
		return params;
	};
})();

// The list is a place for the workspace's extensions (one_studio/places.py):
// told the projects on the page, it lends a spot above them.
function told(listview) {
	const places = onedesk.places;
	listview.$one_spot && listview.$one_spot.remove();
	listview.$one_spot = null;
	if (!places || !places.listening("oneproject_list.projects")) return;
	const rows = (listview.data || []).map((doc) => ({
		name: doc.name,
		title: doc.project_name || doc.name,
		status: doc.status,
		health: doc.status === "Open" ? doc.one_health || null : null,
		kind: doc.one_kind || null,
		customer: doc.customer || null,
		ends: doc.expected_end_date || null,
		percent_complete: Math.round(doc.percent_complete || 0),
	}));
	places.emit(
		"oneproject_list.projects",
		{ projects: { count: rows.length, rows } },
		places.spot(($spot) => {
			listview.$one_spot = $spot;
			$spot.addClass("px-3 pt-3").insertBefore(listview.$result);
		})
	);
}

frappe.listview_settings["Project"] = Object.assign(frappe.listview_settings["Project"] || {}, {
	hide_name_column: true,
	hide_name_filter: true,
	// Every project, finished ones too, as the rail's Projects says. ERPNext
	// opens on Open alone, which also brings its own "Open" layout and its
	// columns (List Filter, Project-Open) in place of these.
	filters: [],
	// OneProject's panel lists its four places (project_places.js): the rest
	// of its setup is in this menu. Projects Settings has four ticks about time; it is opened from here
	// by whoever may change it.
	onload(listview) {
		if (frappe.model.can_read("Activity Type")) {
			listview.page.add_menu_item(__("Rates"), () => frappe.set_route("List", "Activity Type"));
		}
		if (frappe.model.can_write("Projects Settings")) {
			listview.page.add_menu_item(__("Projects Settings"), () => frappe.set_route("Form", "Projects Settings"));
		}
	},
	// A bar on the Timeline says how far along it is and when it ends.
	gantt_custom_popup_html(task, item) {
		const ends = item && item.expected_end_date ? frappe.datetime.str_to_user(item.expected_end_date) : "";
		const done = __("{0}% done", [Math.round((item && item.percent_complete) || 0)]);
		return `<div class="title">${frappe.utils.escape_html(task.name)}</div>
			<div class="subtitle">${[done, ends].filter(Boolean).join(" · ")}</div>`;
	},
	get_indicator(doc) {
		if (doc.status === "Open" && doc.one_health) {
			return [__(doc.one_health), HEALTH[doc.one_health] || "gray", `one_health,=,${doc.one_health}`];
		}
		const colour = { Open: "blue", "On hold": "orange", Completed: "green", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), colour, `status,=,${doc.status}`];
	},
	formatters: {
		// frappe draws the bar alone; the figure is beside it.
		percent_complete(value) {
			const done = Math.round(value || 0);
			return `<div class="flex align-center" style="gap: var(--padding-sm); width: 100%;">
				<div class="progress" style="margin: 0; flex: 1;">
					<div class="progress-bar progress-bar-success" role="progressbar" aria-valuenow="${done}"
						aria-valuemin="0" aria-valuemax="100" style="width: ${done}%;"></div>
				</div>
				<span class="text-muted">${frappe.format(done, { fieldtype: "Percent", precision: 0 }, { inline: true })}</span>
			</div>`;
		},
		project_name(value, df, doc) {
			const up = doc.one_parent && ONE_PARENTS[doc.one_parent];
			return up ? `${value} · ${up}` : value;
		},
	},
	// The parents on the page are known before its rows are drawn.
	before_render() {
		const listview = window.cur_list;
		if (listview && listview.doctype === "Project") {
			for (const doc of listview.data || []) ONE_PARENTS[doc.name] = doc.project_name || doc.name;
		}
	},
	refresh(listview) {
		told(listview);
		const missing = [...new Set(listview.data.map((doc) => doc.one_parent))].filter(
			(name) => name && !(name in ONE_PARENTS)
		);
		if (!missing.length) return quiet(listview);
		frappe.db
			.get_list("Project", { filters: { name: ["in", missing] }, fields: ["name", "project_name"], limit: missing.length })
			.then((rows) => {
				for (const name of missing) ONE_PARENTS[name] = name;
				for (const row of rows) ONE_PARENTS[row.name] = row.project_name || row.name;
				listview.render();
				quiet(listview);
			});
	},
});

// The Timeline leaves out an employee's onboarding or exit checklist, as the
// rail's Projects and the Tree do (one_hr/lifecycle.py); it reads the type.
// The pill reads the health, and the name the project it is under.
(frappe.listview_settings["Project"].add_fields = frappe.listview_settings["Project"].add_fields || []).push(
	"status",
	"one_kind",
	"customer",
	"expected_end_date",
	"percent_complete",
	"project_type",
	"one_health",
	"one_parent"
);

// The other views of Projects.
(() => {
	const Report = frappe.views.ReportView;
	if (Report && !Report.prototype.one_projects) {
		Report.prototype.one_projects = true;
		// The ID column already reads as the project's name (Project shows its
		// title in a link) and opens it, so it is the Project column, and the
		// Project Name column beside it would only say the same again.
		const fields = Report.prototype.set_default_fields;
		Report.prototype.set_default_fields = function () {
			fields.call(this);
			if (this.doctype === "Project") {
				this.fields = this.fields.filter(([name]) => !["project_name", "one_cover"].includes(name));
			}
		};
		// The name is asked for with the rows, so the Project column reads it
		// rather than the ID frappe draws until it learns the title.
		const asked = Report.prototype.get_fields;
		Report.prototype.get_fields = function () {
			const fields = asked.call(this);
			const name = frappe.model.get_full_column_name("project_name", "Project");
			return this.doctype === "Project" && !fields.includes(name) ? [...fields, name] : fields;
		};
		const prepare = Report.prototype.prepare_data;
		Report.prototype.prepare_data = function (r) {
			prepare.call(this, r);
			if (this.doctype !== "Project") return;
			for (const row of this.data || []) {
				if (row.project_name) frappe.utils.add_link_title("Project", row.name, row.project_name);
			}
		};
		const column = Report.prototype.build_column;
		Report.prototype.build_column = function (c) {
			const built = column.call(this, c);
			if (built && this.doctype === "Project" && c[0] === "name" && (c[1] || "Project") === "Project") {
				built.name = built.content = __("Project");
			}
			// Health is how an open project is going: a finished or cancelled
			// one says nothing there, as its pill and its head say nothing.
			if (built && this.doctype === "Project" && c[0] === "one_health") {
				const format = built.format;
				built.format = (value, row, column, data) => {
					const status = data?.status ?? (Array.isArray(row) ? row.find((one) => one.column?.docfield?.fieldname === "status")?.content : row?.status);
					return ["Completed", "Cancelled"].includes(status) ? "" : format(value, row, column, data);
				};
			}
			return built;
		};
	}

	// The dashboard is OneProject's cards and charts (one_project/number_card,
	// one_project/dashboard_chart). ERPNext's two count every project, the
	// HR checklists with them, by when it was last changed.
	const Dashboard = frappe.views.DashboardView;
	if (Dashboard && !Dashboard.prototype.one_projects) {
		Dashboard.prototype.one_projects = true;
		// Where things stand first, then who and what for, then over time.
		const ORDER = [
			"Projects Under Way",
			"Projects at Risk",
			"Projects Past Due",
			"Projects by Health",
			"Projects by Kind",
			"Projects by Manager",
			"Projects by Customer",
			"Projects Started",
		];
		const fetch = Dashboard.prototype.fetch_dashboard_items;
		Dashboard.prototype.fetch_dashboard_items = function (doctype, filters, obj_name) {
			if (this.doctype !== "Project") return fetch.call(this, doctype, filters, obj_name);
			return fetch.call(this, doctype, { ...filters, module: "One Project" }, obj_name).then(() => {
				this[obj_name].sort((a, b) => ORDER.indexOf(a.name) - ORDER.indexOf(b.name));
				// Twelve months read better across the page.
				for (const item of this[obj_name]) if (item.timeseries) item.width = "Full";
			});
		};
	}
})();
