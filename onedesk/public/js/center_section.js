// A centre's tab whose body is an Editor (shell.js): the section is loaded
// from a server module's `load` and saved through its `save`, so a form is
// saved, refused when somebody saved first, and heard when it changes, as
// anywhere else in One. AccountCenter, AccessCenter's workspace roles, and
// One's, OneHR's and OneCalendar's ControlCenters draw their sections on it.
frappe.provide("onedesk.center_section");

// What an Editor uses of a page, kept by the panel's header instead: the
// title's indicator, the primary action and the buttons beside it. A
// dialog is its own place, so there are no breadcrumbs.
onedesk.center_section.page = (panel) => {
	const $actions = () => panel.$header.find(".settings-dialog-panel-actions");
	const $title = () => panel.$header.find(".settings-dialog-panel-title");
	return {
		wrapper: [{}],
		set_indicator(label, colour) {
			this.clear_indicator();
			$title().append(`<span class="one-center-status">${frappe.ui.badge.html({ label, theme: colour })}</span>`);
		},
		clear_indicator() {
			$title().find(".one-center-status").remove();
		},
		set_primary_action(label, click, icon) {
			this.clear_primary_action();
			$(frappe.ui.button.html({ label, icon, variant: "solid" })).addClass("one-center-primary").on("click", click).appendTo($actions());
			panel.$header.removeClass("hide");
		},
		clear_primary_action() {
			$actions().find(".one-center-primary").remove();
		},
		// A group's actions are one menu named for it, and the rest share a
		// menu of their own, so the header keeps to a few buttons.
		add_inner_button(label, action, group = null) {
			const name = group || "more";
			let $menu = $actions().find(`.one-center-inner[data-group="${CSS.escape(name)}"]`);
			if (!$menu.length) {
				$menu = $(`<div class="dropdown one-center-inner"><div class="dropdown-menu dropdown-menu-right"></div></div>`)
					.attr("data-group", name)
					.prependTo($actions());
				$(
					frappe.ui.button.html({
						label: group || "",
						icon: group ? null : "ellipsis",
						variant: "subtle",
						attrs: { "data-toggle": "dropdown", "aria-label": group || __("More") },
					})
				).prependTo($menu);
			}
			$(`<a class="dropdown-item" href="#"></a>`)
				.text(label)
				.on("click", (event) => {
					event.preventDefault();
					action();
				})
				.appendTo($menu.find(".dropdown-menu"));
			panel.$header.removeClass("hide");
		},
		clear_inner_toolbar() {
			$actions().find(".one-center-inner").remove();
		},
		set_breadcrumbs() {},
	};
};

// `API` is the server module the sections load from and save through, and
// `HERE` the page OneAI is told the reader is on (oneai.js `where`).
onedesk.CenterSection = class CenterSection extends onedesk.shell.Editor {
	static API = "";
	static HERE = "";
	static LABEL = "";

	constructor(panel, key) {
		super(onedesk.center_section.page(panel));
		this.panel = panel;
		this.key = key;
	}

	// The server says the section changed in another tab or by somebody else.
	heard(event, key) {
		frappe.realtime.on(event, () => this.key === key && this.$content && this.$content.is(":visible") && this.refresh());
	}

	body() {
		return $(`<div class="one-shell-body one-center-body" data-tour="center-section"></div>`).appendTo(this.panel.body.empty());
	}

	async open(key = this.key, { record = null } = {}) {
		const kind = this.constructor;
		this.key = key;
		this.record = record;
		this.trailed = false;
		onedesk.centers.here = { page: kind.HERE, section: key, record: record || "", label: kind.LABEL };
		this.panel.set_header(this.panel.item);
		this.unsaved();
		this.$content = this.body().html(onedesk.shell.quiet(__("Loading…")));
		try {
			this.data = await frappe.xcall(kind.API + "load", { section: key, record });
		} catch (e) {
			this.$content.html(frappe.ui.alert.html({ title: __("Could Not Open This"), theme: "red" }));
			return;
		}
		if (this.loaded) this.loaded(this.data);
		this.$content.empty();
		this.hear(this.data.opened);
		this.links();
		this[`draw_${key}`](this.data);
	}

	saver(values) {
		return { method: this.constructor.API + "save", args: { section: this.key, values, record: this.record } };
	}

	redraw(said) {
		if (said.record !== undefined && said.record !== this.record) return this.open(this.key, { record: said.record });
		if (this.trailed) {
			this.unsaved();
			this.panel.set_header(this.panel.item);
			this.$content = this.body();
			this.links();
		}
		this[`draw_${this.key}`](said);
	}

	refresh() {
		this.open(this.key, { record: this.record });
	}

	// One record of a section, such as a person in People: its name heads the
	// panel, with Back to the section before it.
	as_record(record) {
		this.trailed = true;
		this.status = record.status || null;
		this.panel.set_header({ title: record.title });
		this.panel.one_back(() => this.open(this.key));
		this.$content = onedesk.shell.record(this.$content, { ...record, parent: null, page: this.page });
		return this.$content;
	}

	// A link to another section of the centre (#people) opens its tab, a link
	// to another centre (/desk/one?center=account&at=people) opens that one in
	// its place, and a link anywhere else in One closes the centre first.
	links() {
		this.$content.on("click", 'a[href^="#"]', (event) => {
			event.preventDefault();
			this.panel.dialog.activate($(event.currentTarget).attr("href").slice(1));
		});
		this.$content.on("click", 'a[href^="/desk"]', (event) => {
			const asked = Object.fromEntries(new URL($(event.currentTarget).attr("href"), location.origin).searchParams);
			this.panel.dialog.hide();
			if (!asked.center) return;
			event.preventDefault();
			onedesk.centers.open(asked.center, asked);
		});
	}

	// Going somewhere else in One closes the centre first.
	leave(go) {
		this.panel.dialog.hide();
		go();
	}
};

// A tab of a centre drawn by a CenterSection: `Kind` the class, `about`
// what it is for, and `record` the one record to open it on.
onedesk.center_section.tab = (Kind, { id, label, title = null, icon, about, record = null, needs = null }) => ({
	id,
	label,
	icon,
	title: title || label,
	description: about,
	needs,
	render(panel) {
		panel.section = panel.section || new Kind(panel, id);
		panel.section.open(id, { record });
	},
});
