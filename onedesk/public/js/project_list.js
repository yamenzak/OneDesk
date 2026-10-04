// Projects: where each one stands, in one pill. An open project's pill is its
// health (On Track, At Risk, Off Track), since every open project would
// otherwise read "Open"; a finished one says Completed or Cancelled. ERPNext's
// list put "33%" in place of Open once a task was done; how far it has got is
// its own column. The manager reads as a name because every link to a person
// does (`show_title_field_in_link` on User).
//
// A sub-project reads after the project it is under, "Villa Al Barsha ›
// Handrails", the way My Tasks names where a task is (one_project/tree.py
// `path`): a parent on the page is read off the page, one that isn't is
// asked for once, and the parent's part is drawn quieter than the name.
const ONE_PARENTS = {};
const HEALTH = { "On Track": "green", "At Risk": "orange", "Off Track": "red" };

// The parent's part of the name, quieter: frappe writes the name as text.
function quiet(listview) {
	listview.$result.find(".list-row a.ellipsis[data-name]").each((_, link) => {
		const doc = listview.data.find((one) => one.name === link.dataset.name);
		const up = doc && doc.one_parent && ONE_PARENTS[doc.one_parent];
		if (!up || link.querySelector(".text-muted") || !link.textContent.startsWith(`${up} › `)) return;
		link.replaceChildren(
			Object.assign(document.createElement("span"), { className: "text-muted", textContent: `${up} › ` }),
			document.createTextNode(link.textContent.slice(up.length + 3))
		);
	});
}

frappe.listview_settings["Project"] = Object.assign(frappe.listview_settings["Project"] || {}, {
	hide_name_column: true,
	hide_name_filter: true,
	// Every view of Projects (Report, Kanban, Dashboard) leaves out an
	// employee's onboarding or exit checklist until somebody clears the
	// filter, as the rail's Projects row does.
	filters: [["project_type", "!=", "Employee Boarding"]],
	// Projects Settings has four ticks about time; it is opened from here by
	// whoever may change it, rather than taking a row in the rail.
	onload(listview) {
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
		const colour = { Open: "blue", Completed: "green", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), colour, `status,=,${doc.status}`];
	},
	formatters: {
		project_name(value, df, doc) {
			const up = doc.one_parent && ONE_PARENTS[doc.one_parent];
			return up ? `${up} › ${value}` : value;
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
			if (this.doctype === "Project") this.fields = this.fields.filter(([name]) => name !== "project_name");
		};
		const column = Report.prototype.build_column;
		Report.prototype.build_column = function (c) {
			const built = column.call(this, c);
			if (built && this.doctype === "Project" && c[0] === "name" && (c[1] || "Project") === "Project") {
				built.name = built.content = __("Project");
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

	// A project is a stretch of weeks, drawn on the Timeline (Gantt); a month
	// grid of the same bars says less, so Projects has no Calendar view.
	const Select = frappe.views.ListViewSelect;
	if (Select && !Select.prototype.one_projects) {
		Select.prototype.one_projects = true;
		const views = Select.prototype.get_views;
		Select.prototype.get_views = function () {
			const found = views.call(this);
			if (this.doctype === "Project") delete found.Calendar;
			return found;
		};
	}
})();
