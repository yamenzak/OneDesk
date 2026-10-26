frappe.provide("onedesk.roles");

// A module's role builder, drawn in a tab of its settings dialog: the
// module's abilities as rows, in its groups, and its roles as columns, User,
// the workspace's own, Manager (one/access.py matrix_of, docs/ROLES.md).
// Each cell saves as it changes. A role above User never offers less than
// User has, so its cell starts at User's value. The abilities' column stays
// put while the roles scroll under it, and which roles show is the reader's
// own choice, kept in their user settings (onedesk.roles.pick).
onedesk.roles.hidden = async (app) => {
	const said = (await frappe.model.user_settings.get("One Roles")) || {};
	return said[app] || [];
};

onedesk.roles.draw = async (panel, app, said = null) => {
	const A = "onedesk.one.access.";
	const esc = frappe.utils.escape_html;
	const was = (panel.shown = (panel.shown || 0) + 1);
	said = said || (await frappe.xcall(A + "ability_matrix", { app }));
	if (panel.shown !== was) return;
	const named = (role) => (role.own ? role.name : __(role.name));
	const hidden = await onedesk.roles.hidden(app);
	if (panel.shown !== was) return;
	const shown = said.roles.filter((role) => !hidden.includes(role.key));
	said = { ...said, roles: shown.length ? shown : said.roles };
	const $body = panel.body.empty();
	const $table = $(`<table class="rm-table"></table>`).appendTo($(`<div class="rm-scroll"></div>`).appendTo($body));

	const $top = $(`<tr><th class="rm-ability" scope="col"><span class="sr-only">${esc(__("Ability"))}</span></th></tr>`);
	$(`<thead></thead>`).append($top).appendTo($table);
	said.roles.forEach((role) => {
		const people = `<span class="rm-people">${esc(role.people === 1 ? __("1 Person") : __("{0} People", [role.people]))}</span>`;
		const $th = $(`<th class="rm-role" scope="col"></th>`).appendTo($top);
		if (!role.own) return $th.html(`<span class="rm-role-name">${esc(named(role))}</span>${people}`);
		$(`<button type="button" class="rm-role-name rm-role-edit">${esc(role.name)}${frappe.utils.icon("pencil", "xs")}</button>`)
			.attr({ title: __("Edit {0}", [role.name]) })
			.on("click", () => onedesk.roles.edit(panel, app, role))
			.appendTo($th);
		$th.append(people);
	});

	const change = async (role, row, value) => {
		const next = await frappe.xcall(A + "change_ability", { key: role.key, ability: row.key, value });
		frappe.show_alert({ message: __("Saved"), indicator: "green" });
		onedesk.roles.draw(panel, app, next);
	};
	const $rows = $(`<tbody></tbody>`).appendTo($table);
	said.groups.forEach((group) => {
		$rows.append(`<tr class="rm-group"><th colspan="${said.roles.length + 1}" scope="colgroup"><span class="rm-group-label">${esc(group.label)}</span></th></tr>`);
		group.rows.forEach((row) => {
			const $tr = $(`<tr></tr>`).appendTo($rows);
			$tr.append(
				`<th class="rm-ability" scope="row"><span class="rm-label">${esc(row.label)}</span>${
					row.about ? `<span class="rm-about">${esc(row.about)}</span>` : ""
				}</th>`
			);
			said.roles.forEach((role) => {
				const value = said.values[role.key][row.key];
				const least = (said.least[role.key] || {})[row.key];
				const $cell = $(`<td class="rm-cell"></td>`).appendTo($tr);
				const label = `${named(role)}: ${row.label}`;
				if (row.kind === "switch") {
					const control = frappe.ui.form.make_control({
						df: { fieldtype: "Switch", fieldname: row.key, label: "" },
						parent: $cell,
						render_input: true,
					});
					control.set_value(value ? 1 : 0);
					control.$input.attr("aria-label", label).prop("disabled", Boolean(least));
					if (least) $cell.attr("title", __("A role above User has everything User has."));
					control.$input.on("change", () => change(role, row, control.get_value() ? 1 : 0));
					return;
				}
				const from = least ? row.options.findIndex((one) => one.value === least) : 0;
				const control = frappe.ui.form.make_control({
					df: { fieldtype: "Select", fieldname: row.key, label: "", options: row.options.slice(from) },
					parent: $cell,
					render_input: true,
				});
				control.set_value(value);
				control.$input.attr("aria-label", label).on("change", () => change(role, row, control.get_value()));
			});
		});
	});
};

onedesk.roles.pick = async (panel, app) => {
	const said = await frappe.xcall("onedesk.one.access.ability_matrix", { app });
	const hidden = await onedesk.roles.hidden(app);
	const dialog = new frappe.ui.Dialog({
		title: __("Show Roles"),
		fields: [
			{
				fieldname: "roles",
				fieldtype: "MultiCheck",
				columns: 2,
				sort_options: false,
				options: said.roles.map((role) => ({
					label: role.own ? role.name : __(role.name),
					value: role.key,
					checked: !hidden.includes(role.key),
				})),
			},
		],
		primary_action_label: __("Show"),
		primary_action: async ({ roles }) => {
			if (!roles.length) return frappe.show_alert({ message: __("Choose at least one role."), indicator: "orange" });
			await frappe.model.user_settings.save("One Roles", app, said.roles.map((role) => role.key).filter((key) => !roles.includes(key)));
			dialog.hide();
			onedesk.roles.draw(panel, app);
		},
	});
	dialog.show();
};

onedesk.roles.create = (panel, app) => {
	const dialog = new frappe.ui.Dialog({
		title: __("New Role"),
		fields: [
			{ fieldname: "title", fieldtype: "Data", label: __("Name"), reqd: 1, description: __("For example, HR Team.") },
			{ fieldname: "start", fieldtype: "Select", label: __("Based On"), reqd: 1, default: "User", options: [] },
		],
		primary_action_label: __("Create"),
		primary_action: async ({ title, start }) => {
			await frappe.xcall("onedesk.one.access.make_level", { app, title, start });
			dialog.hide();
			onedesk.roles.draw(panel, app);
		},
	});
	frappe.xcall("onedesk.one.access.ability_matrix", { app }).then((said) => {
		const field = dialog.get_field("start");
		field.df.options = said.roles.map((role) => ({ value: role.name, label: role.own ? role.name : __(role.name) }));
		field.df.description = __("Starts with this role's abilities and permissions.");
		field.refresh();
		dialog.set_value("start", "User");
	});
	dialog.show();
};

onedesk.roles.edit = (panel, app, role) => {
	const dialog = new frappe.ui.Dialog({
		title: role.name,
		fields: [{ fieldname: "title", fieldtype: "Data", label: __("Name"), reqd: 1, default: role.name }],
		primary_action_label: __("Save"),
		primary_action: async ({ title }) => {
			await frappe.xcall("onedesk.one.access.rename_role", { name: role.name, title });
			dialog.hide();
			onedesk.roles.draw(panel, app);
		},
		secondary_action_label: __("Delete"),
		secondary_action: () =>
			frappe.confirm(__("Delete {0}? This removes its permissions.", [frappe.utils.escape_html(role.name)]), async () => {
				await frappe.xcall("onedesk.one.access.remove_level", { name: role.name });
				dialog.hide();
				onedesk.roles.draw(panel, app);
			}),
	});
	dialog.show();
};
