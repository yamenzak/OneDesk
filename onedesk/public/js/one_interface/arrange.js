// Arrange Apps (one/rail.py): a person's own order of the rail, saved as
// their layer of frappe's dock through frappe's save_user_dock, and their
// folders, One's layer in their user settings. Reset saves the layer empty,
// which frappe reads as no opinion, so the workspace's order shows again.
// SetupCenter's Order of Apps draws the same list for the workspace.
frappe.provide("onedesk.rail");

onedesk.rail.SAVE = "frappe.desk.doctype.dock.dock.save_user_dock";

/** A list of apps to drag into order, each row with a folder to pick when
 * `folders` is given ({key: name}). Returns what reads the order back. */
onedesk.rail.sortable = ($into, apps, folders = null) => {
	const esc = frappe.utils.escape_html;
	const $list = $(`<div class="one-arrange" role="list"></div>`).appendTo($into);
	const named = () => [...new Set(Object.values(folders || {}).filter(Boolean))];
	const pick = ($button, key) => {
		const set = (name) => {
			folders[key] = name || null;
			frappe.ui.button.dress($button, { label: name || __("No Folder"), icon: "folder", variant: "ghost" });
		};
		new frappe.ui.Dropdown({
			trigger: $button,
			align: "end",
			options: () => [
				{ group: "", options: [{ label: __("No Folder"), onclick: () => set(null) }, ...named().map((name) => ({ label: name, icon: "folder", onclick: () => set(name) }))] },
				{
					group: "",
					options: [
						{
							label: __("New Folder"),
							icon: "folder-plus",
							onclick: () =>
								frappe.prompt({ fieldname: "name", fieldtype: "Data", label: __("Folder Name"), reqd: 1 }, ({ name }) => set(name.trim()), __("New Folder"), __("Create")),
						},
					],
				},
			],
		});
		set(folders[key]);
	};
	for (const app of apps) {
		const $row = $(`<div class="one-arrange-row" role="listitem" data-key="${esc(app.key)}">
			<span class="one-arrange-grip">${frappe.utils.icon("grip-vertical", "sm")}</span>
			<span class="one-arrange-icon">${frappe.utils.icon(app.icon || "app-window", "md")}</span>
			<span class="one-arrange-name"></span>
		</div>`).appendTo($list);
		$row.find(".one-arrange-name").text(app.label);
		if (folders) {
			const $button = $(frappe.ui.button.html({ label: __("No Folder"), icon: "folder", variant: "ghost", css_class: "one-arrange-folder" })).appendTo($row);
			pick($button, app.key);
		}
	}
	new Sortable($list[0], { handle: ".one-arrange-grip", animation: 150 });
	return () => $list.children(".one-arrange-row").map((_i, el) => el.dataset.key).get();
};

onedesk.rail.arrange = () => {
	const rail = onedesk.rail;
	const app = rail.app();
	const entries = rail.entries();
	if (!app || !entries.length) return;
	const by = Object.fromEntries(entries.map((one) => [rail.key(one), one]));
	const folders = {};
	for (const folder of rail.folders(entries)) for (const key of folder.apps) folders[key] = folder.name;
	const done = (dock, message) => {
		frappe.boot.dock = { ...(frappe.boot.dock || {}), [app.app_name]: dock };
		rail.redraw();
		dialog.hide();
		frappe.show_alert({ message, indicator: "green" });
	};
	const dialog = new frappe.ui.Dialog({
		title: __("Arrange Apps"),
		fields: [{ fieldtype: "HTML", fieldname: "apps" }],
		primary_action_label: __("Save"),
		primary_action: async () => {
			const keys = order();
			const items = keys.map((key) => ({ link_type: by[key].link_type, link_to: by[key].link_to, url: by[key].url }));
			const dock = await frappe.xcall(rail.SAVE, { app: app.app_name, items: JSON.stringify(items) });
			const grouped = [];
			for (const key of keys) {
				const name = folders[key];
				if (!name) continue;
				let folder = grouped.find((one) => one.name === name);
				if (!folder) grouped.push((folder = { name, apps: [] }));
				folder.apps.push(key);
			}
			await rail.keep("folders", grouped);
			done(dock, __("Apps arranged"));
		},
		secondary_action_label: __("Reset"),
		secondary_action: () =>
			frappe.warn(
				__("Reset Your Apps?"),
				__("The rail goes back to the workspace's order, and your folders are removed."),
				async () => {
					const dock = await frappe.xcall(rail.SAVE, { app: app.app_name, items: "[]" });
					await rail.keep("folders", []);
					done(dock, __("Apps reset"));
				},
				__("Reset Apps")
			),
	});
	const order = rail.sortable(
		dialog.fields_dict.apps.$wrapper,
		entries.map((one) => ({ key: rail.key(one), label: one.label, icon: one.icon })),
		folders
	);
	dialog.show();
};
