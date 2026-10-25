// One settings dialog for every module (docs/READY.md, mechanism 5):
// frappe's settings dialog with the module's mark and Help at the top of
// its sidebar, and its tabs left out where the reader's role can't use them.
// The kit is what a module's tabs are drawn with, so every module's settings
// look and behave alike: list rows, headings with a control at their end,
// a switch after a tab's title, Back before a view's title, a Save that
// shows once something changed.
frappe.provide("onedesk.module_settings");

// The centres a module's dialogs are, named as One's products are: One's
// mark, the first word light and Center after it (HelpCenter, ControlCenter,
// AccountCenter, UpdateCenter, TrustCenter, AccessCenter,
// NotificationCenter). They are names, so they are not translated.
onedesk.CENTERS = {
	help: "Help",
	settings: "Control",
	account: "Account",
	updates: "Update",
	trust: "Trust",
	access: "Access",
	notifications: "Notification",
};

// The top of a dialog's sidebar: the centre it is, and under it, small,
// whose it is: a module (its mark and name) or one thing in it (an icon and
// a label, such as a mailbox's address).
onedesk.module_head = ($into, { center, module = null, label = null, icon = null }) => {
	const $head = $(`<div class="one-module-head"></div>`).prependTo($into);
	const name = document.createElement("span");
	name.className = "one-name one-solo";
	name.innerHTML = frappe.utils.icon("one", { width: "1.05em", height: "1.05em" }, "", "", "one-mark");
	const word = document.createElement("span");
	const light = document.createElement("span");
	light.className = "one-light";
	light.textContent = onedesk.CENTERS[center] || center;
	word.append(light, "Center");
	name.append(word);
	$(`<div class="one-module-head-name"></div>`).append(name).appendTo($head);
	const $of = $(`<div class="one-module-head-of"></div>`).appendTo($head);
	const rest = module && module.replace(/^One/, "");
	if (module && rest !== module) $of.append(onedesk.brand.named(rest, true));
	else {
		if (icon) $of.append(frappe.utils.icon(icon, "xs"));
		$(`<span></span>`).text(label || module || "").appendTo($of);
	}
	$(`<div class="one-module-head-tools"></div>`).appendTo($head);
	return $head;
};

// A button at the top of a centre, beside its name: Help, or the arrows
// that open the whole of it (`expand`).
onedesk.module_head_tool = ($head, { icon, title, click }) =>
	$(frappe.ui.button.html({ variant: "ghost", icon, title, attrs: { "aria-label": title } }))
		.on("click", click)
		.appendTo($head.find(".one-module-head-tools"));

// Every centre opened on a part of One opens the whole of it from the same
// arrows: a module's HelpCenter all of One's help, its ControlCenter the
// workspace's settings, an AccountCenter the module's ControlCenter.
onedesk.module_head_expand = ($head, open) =>
	onedesk.module_head_tool($head, { icon: "maximize-2", title: __("Open All"), click: open });

onedesk.module_settings.Dialog = class ModuleSettingsDialog extends frappe.ui.SettingsDialog {
	render_sidebar() {
		super.render_sidebar();
		// A module's settings are its ControlCenter; a dialog showing one thing
		// in it, such as a mailbox, says which (`dialog.center`).
		// `center` is a centre's key, on a module or on the whole workspace,
		// or an object naming one thing in a module.
		const center =
			this.center && typeof this.center === "object"
				? this.center
				: this.module
				? { center: this.center || "settings", module: this.module }
				: { center: this.center, label: __("Your Workspace"), icon: "building" };
		const $head = onedesk.module_head(this.$sidebar, center);
		if (["settings", "account"].includes(center.center) && frappe.boot.one_versions && frappe.boot.one_versions[this.module]) {
			onedesk.module_head_tool($head, { icon: "circle-question-mark", title: __("Help"), click: () => onedesk.help.open(this.module) });
		}
		onedesk.module_head_expand($head, () => {
			if (this.expand) return this.expand();
			this.hide();
			frappe.set_route("one", frappe.boot.one_administers ? "workspace-settings" : "settings");
		});
	}

	// A row that is another centre (`opens`) opens it rather than a tab.
	activate(id) {
		const item = this._items[id];
		if (item && item.opens) {
			this.hide();
			item.opens();
			return;
		}
		super.activate(id);
	}

	make_tab_item(item) {
		const $item = super.make_tab_item(item);
		if (item.opens) $item.addClass("one-set-opens").find(".settings-dialog-tab-item-content").append(frappe.utils.icon("arrow-up-right", "xs"));
		return $item;
	}
};

// Whether the reader's role allows a tab: `needs` is an ability's key, a
// list of keys any one of which will do, or a function of them all.
onedesk.module_settings.allows = (needs, may) => {
	if (!needs) return true;
	if (typeof needs === "function") return !!needs(may);
	return [].concat(needs).some((key) => may[key]);
};

// A module's setup steps the reader may do (docs/READY.md, mechanism 9;
// one/setup_steps.py): each done, or a to-do with Set Up, which opens the
// tab that does it, and Mark as Done.
onedesk.module_settings.getting_started = (module) => ({
	id: "getting_started",
	label: __("Getting Started"),
	icon: "list-checks",
	title: __("Getting Started"),
	description: __("What to set up so {0} works the way your company does.", [module]),
	render(panel) {
		const kit = onedesk.module_settings.kit;
		const steps = (frappe.boot.one_setup || {})[module] || [];
		const $list = $(`<div class="one-set-list one-set-steps"></div>`).appendTo(panel.body.empty());
		for (const step of steps) {
			const $end = $(`<span class="one-set-buttons"></span>`);
			if (step.done) {
				$end.append(frappe.ui.badge.html({ label: __("Done"), theme: "green" }));
			} else {
				if (step.tab && panel.dialog._items[step.tab]) {
					kit.button({ label: __("Set Up"), variant: "solid" }).on("click", () => panel.dialog.activate(step.tab)).appendTo($end);
				}
				kit.button({ label: __("Mark as Done"), variant: "ghost" })
					.on("click", async () => {
						const left = await frappe.xcall("onedesk.one.setup_steps.finish", { module, key: step.key });
						frappe.boot.one_setup[module] = left;
						panel.refresh();
					})
					.appendTo($end);
			}
			kit.row({ lead: kit.glyph(step.done ? "circle-check" : "circle"), title: step.title, sub: frappe.utils.escape_html(step.about) })
				.appendTo($list)
				.find(".one-set-end")
				.append($end);
		}
	},
});

// What every module's ControlCenter ends with, found rather than drawn
// (docs/READY.md, mechanisms 14 and 15): Roles and Access for a module that
// declares abilities, to its administrators, and Notifications for a module
// that sends any, each opening its centre on the module.
onedesk.module_settings.centers = (module) => {
	const has = frappe.boot.one_centers || {};
	const items = [];
	if ((has.access || []).includes(module)) {
		items.push({ id: "access_center", label: __("Roles and Access"), icon: "key-round", opens: () => onedesk.access.open({ module }) });
	}
	if ((has.notifications || []).includes(module)) {
		items.push({ id: "notification_center", label: __("Notifications"), icon: "bell", opens: () => onedesk.notification_center.open({ module }) });
	}
	return items.length ? [{ group: null, items }] : [];
};

// The dialog for a module: `tabs` as frappe's settings dialog takes them,
// each item with the `needs` its tab asks of the reader's role (`may`).
// A group left with nothing is left out, and opening again replaces it.
onedesk.module_settings.open = ({ module, may = {}, tabs, default_tab = null, ...rest }) => {
	// Every module's ControlCenter starts with what is left to set up, while
	// something is. What it adds to the agreements is in TrustCenter.
	const steps = (frappe.boot.one_setup || {})[module] || [];
	const starting = steps.some((step) => !step.done) ? [{ group: __("Start Here"), items: [onedesk.module_settings.getting_started(module)] }] : [];
	tabs = [...starting, ...tabs, ...onedesk.module_settings.centers(module)];
	const shown = tabs
		.map((group) => ({ ...group, items: (group.items || []).filter((item) => item && onedesk.module_settings.allows(item.needs, may)) }))
		.filter((group) => group.items.length);
	const ids = shown.flatMap((group) => group.items.map((item) => item.id));
	const open = onedesk.module_settings._open || {};
	if (open[module]) open[module].$wrapper.remove();
	const dialog = new onedesk.module_settings.Dialog({
		title: __("{0} Settings", [module]),
		module,
		tabs: shown,
		default_tab: ids.includes(default_tab) ? default_tab : ids[0],
		...rest,
	});
	dialog.$wrapper.addClass("one-set");
	// What the dialog opened with, for a module that swaps its tabs (one
	// mailbox's) and goes back.
	dialog.home = shown;
	open[module] = dialog;
	onedesk.module_settings._open = open;
	return dialog;
};

onedesk.module_settings.kit = (() => {
	const esc = frappe.utils.escape_html;
	const saved = () => frappe.show_alert({ message: __("Saved"), indicator: "green" });

	const heading = (title, description) =>
		`<div class="settings-dialog-section-heading"><div class="settings-dialog-section-title">${esc(title)}</div>${
			description ? `<div class="settings-dialog-section-description">${esc(description)}</div>` : ""
		}</div>`;

	// A section heading with a control at its end, such as a picker and Add.
	const heading_with = (title, description) => {
		const $row = $(`<div class="one-set-heading">${heading(title, description)}<span class="one-set-heading-end"></span></div>`);
		return { $row, $end: $row.find(".one-set-heading-end") };
	};

	// A list row: a picture or an icon, two lines, and what sits at its end.
	const row = ({ lead, title, sub = "", end = "", open = null }) => {
		const $row = $(`<div class="one-set-row${open ? " one-set-row-open" : ""}">
			<span class="one-set-lead">${lead}</span>
			<span class="one-set-text"><span class="one-set-title">${esc(title)}</span>${sub ? `<span class="one-set-sub">${sub}</span>` : ""}</span>
			<span class="one-set-end">${end}</span>
		</div>`);
		if (open) {
			$row.attr({ role: "button", tabindex: 0 }).on("click keydown", (e) => {
				if (e.type === "keydown" && e.key !== "Enter") return;
				if ($(e.target).closest(".one-set-end button, .one-set-end input, .one-set-end label").length) return;
				open();
			});
		}
		return $row;
	};
	const glyph = (name) => `<span class="one-set-glyph">${frappe.utils.icon(name, "sm")}</span>`;
	const chevron = () => `<span class="one-set-chevron">${frappe.utils.icon("chevron-right", "sm")}</span>`;
	const empty = (words) => `<div class="one-set-empty">${esc(words)}</div>`;
	const fields = ($into, list) => {
		const group = new frappe.ui.FieldGroup({ fields: list, body: $into.get(0) });
		group.make();
		return group;
	};
	const button = (opts) => $(frappe.ui.button.html(opts));
	const buttons = ($into) => $(`<div class="one-set-buttons"></div>`).appendTo($into);
	const remove = (click) =>
		button({ variant: "ghost", icon: "x", title: __("Remove"), attrs: { "aria-label": __("Remove") } }).on("click", click);

	// A view inside a tab: frappe's panel view, with Back before its title.
	const view = (panel, opts) => {
		panel.shown = (panel.shown || 0) + 1;
		panel.set_view(opts);
		button({ variant: "ghost", icon: "arrow-left", title: __("Back"), attrs: { "aria-label": __("Back") } })
			.addClass("one-set-back")
			.on("click", () => panel.refresh())
			.prependTo(panel.$header.find(".settings-dialog-panel-title"));
		return panel;
	};

	// A tab's Save shows only once something in it changed, and goes again
	// once saved (panel.clean). The editor settles its value after drawing,
	// so the starting values are read a moment later.
	const track = (panel) => {
		const $save = panel.$header.find(".one-set-save").addClass("hide");
		const now = () => JSON.stringify(panel.fieldgroup ? panel.fieldgroup.get_values(true) : {});
		let was = null;
		setTimeout(() => (was = now()), 600);
		const check = () => was !== null && $save.toggleClass("hide", now() === was);
		(panel.fieldgroup?.fields_list || []).forEach((field) => {
			const before = field.df.change;
			field.df.change = function () {
				if (before) before.apply(this, arguments);
				check();
			};
		});
		panel.body.on("input", check);
		panel.clean = () => {
			was = now();
			$save.addClass("hide");
		};
	};

	// A tab's on/off as a switch after its title, saved as it changes; the
	// tab's fields show only while it is on.
	const header_switch = (panel, value, change) => {
		const control = frappe.ui.form.make_control({
			df: { fieldtype: "Switch", fieldname: "on", label: "" },
			parent: $(`<span class="one-set-switch one-set-head-switch"></span>`).appendTo(panel.$header.find(".settings-dialog-panel-title")),
			render_input: true,
		});
		control.set_value(value ? 1 : 0);
		control.$input.attr("aria-label", panel.item.title);
		const shown = (on) => panel.body.toggleClass("hide", !on);
		control.$input.on("change", async () => {
			const on = control.get_value() ? 1 : 0;
			shown(on);
			await change(on);
			saved();
		});
		shown(value);
		return control;
	};

	// A heading with its switch at the end, saved as it changes.
	const switched = ($body, title, description, value, change) => {
		const top = heading_with(title, description);
		top.$row.appendTo($body);
		const control = frappe.ui.form.make_control({
			df: { fieldtype: "Switch", fieldname: "on", label: "" },
			parent: $(`<span class="one-set-switch"></span>`).appendTo(top.$end),
			render_input: true,
		});
		control.set_value(value ? 1 : 0);
		control.$input.on("change", async () => {
			await change(control.get_value() ? 1 : 0);
			saved();
		});
		return control;
	};

	return { esc, saved, heading, heading_with, row, glyph, chevron, empty, fields, button, buttons, remove, view, track, header_switch, switched };
})();
