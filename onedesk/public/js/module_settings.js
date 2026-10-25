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
// AccountCenter, UpdateCenter). They are names, so they are not translated.
onedesk.CENTERS = { help: "Help", settings: "Control", account: "Account", updates: "Update" };

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
	return $head;
};

onedesk.module_settings.Dialog = class ModuleSettingsDialog extends frappe.ui.SettingsDialog {
	render_sidebar() {
		super.render_sidebar();
		// A module's settings are its ControlCenter; a dialog showing one thing
		// in it, such as a mailbox, says which (`dialog.center`).
		const $head = onedesk.module_head(this.$sidebar, this.center || { center: "settings", module: this.module });
		if (frappe.boot.one_versions && frappe.boot.one_versions[this.module]) {
			$(frappe.ui.button.html({ variant: "ghost", icon: "circle-question-mark", title: __("Help"), attrs: { "aria-label": __("Help") } }))
				.addClass("one-module-head-help")
				.on("click", () => onedesk.help.open(this.module))
				.appendTo($head);
		}
	}
};

// Whether the reader's role allows a tab: `needs` is an ability's key, a
// list of keys any one of which will do, or a function of them all.
onedesk.module_settings.allows = (needs, may) => {
	if (!needs) return true;
	if (typeof needs === "function") return !!needs(may);
	return [].concat(needs).some((key) => may[key]);
};

// The dialog for a module: `tabs` as frappe's settings dialog takes them,
// each item with the `needs` its tab asks of the reader's role (`may`).
// A group left with nothing is left out, and opening again replaces it.
onedesk.module_settings.open = ({ module, may = {}, tabs, default_tab = null, ...rest }) => {
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
