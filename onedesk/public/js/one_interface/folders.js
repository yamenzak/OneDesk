// One's layer over frappe's dock (one/rail.py): a person's folders and the
// apps they opened lately, kept in their user settings (One Rail) and naming
// each app by where it goes, as frappe's dock keys it. The order is frappe's
// own layers. A folder stands on the rail where its first app would, and its
// apps open from it beside the rail.
frappe.provide("onedesk.rail");

$.extend(onedesk.rail, {
	SETTINGS: "One Rail",
	RECENT: 8,

	/** The person's layer: frappe's user settings, seeded from the boot. */
	held() {
		const settings = frappe.model.user_settings;
		const boot = frappe.boot.one_rail || {};
		settings[this.SETTINGS] ||= { folders: boot.folders || [], recent: boot.recent || [] };
		return settings[this.SETTINGS];
	},

	keep(key, value) {
		this.held()[key] = value;
		return frappe.model.user_settings.save(this.SETTINGS, key, value);
	},

	/** The app whose dock is One's rail (frappe's app_data). */
	app() {
		const name = frappe.boot.one_rail?.app;
		return (frappe.boot.app_data || []).find((one) => one.app_name === name) || frappe.app?.sidebar?.get_sidebar_app?.() || null;
	},

	/** Every app on the person's rail, in their order, folders unfolded. */
	entries() {
		const sidebar = frappe.app?.sidebar;
		return sidebar ? sidebar.collect_dock_entries(this.app()) : [];
	},

	key(entry) {
		return frappe.app.sidebar.dock_entry_key(entry);
	},

	/** The person's folders, each with the apps still on their rail. */
	folders(entries = this.entries()) {
		const keys = new Set(entries.map((one) => this.key(one)));
		const taken = new Set();
		return (this.held().folders || [])
			.map((one) => ({ name: one.name, apps: (one.apps || []).filter((key) => keys.has(key) && !taken.has(key) && taken.add(key)) }))
			.filter((one) => one.name && one.apps.length);
	},

	/** The rail as drawn: an app, or a folder where its first app stands. */
	laid(entries = this.entries()) {
		const folders = this.folders(entries);
		const home = {};
		for (const folder of folders) for (const key of folder.apps) home[key] = folder;
		const by = Object.fromEntries(entries.map((one) => [this.key(one), one]));
		const out = [];
		const drawn = new Set();
		for (const entry of entries) {
			const folder = home[this.key(entry)];
			if (!folder) out.push({ entry });
			else if (!drawn.has(folder)) {
				drawn.add(folder);
				out.push({ folder, entries: folder.apps.map((key) => by[key]) });
			}
		}
		return out;
	},

	/** The apps opened lately, newest first, then none twice. */
	recent(entries = this.entries()) {
		const by = Object.fromEntries(entries.map((one) => [this.key(one), one]));
		return (this.held().recent || []).map((key) => by[key]).filter(Boolean);
	},

	seen() {
		const module = frappe.app?.sidebar?.current_module;
		const entry = module && this.entries().find((one) => one.module === module);
		if (!entry) return;
		const key = this.key(entry);
		const recent = this.held().recent || [];
		if (recent[0] === key) return;
		this.held().recent = [key, ...recent.filter((one) => one !== key)].slice(0, this.RECENT);
		clearTimeout(this.saving);
		this.saving = setTimeout(() => this.keep("recent", this.held().recent), 1500);
	},

	redraw() {
		const dock = frappe.app?.sidebar?.dock;
		if (!dock) return;
		dock.rendered = null;
		dock.refresh();
	},

	/** A folder's tile on the rail, opening its apps beside it. */
	tile(dock, folder, entries) {
		const esc = frappe.utils.escape_html;
		const active = entries.some((one) => dock.sidebar.is_active_entry(one));
		const $item = $(`<button class="dock-item one-rail-folder ${active ? "active" : ""}" aria-label="${esc(folder.name)}">
			<span class="dock-item-icon">${frappe.utils.icon("folder", "rail")}</span>
			<span class="dock-item-label">${esc(folder.name)}</span>
		</button>`);
		dock.name_tile($item, folder.name);
		new frappe.ui.Dropdown({
			trigger: $item,
			side: "right",
			align: "start",
			options: () => [{ group: "", options: entries.map((one) => ({ label: one.label, icon: one.icon, onclick: () => this.open(one) })) }],
		});
		return $item;
	},

	/** Opens an app as its rail tile does. */
	open(entry) {
		frappe.app.sidebar.dock?.close();
		frappe.app.sidebar.open_dock_entry(entry);
	},
});

{
	const Dock = frappe.ui.Dock;
	if (Dock && !Dock.prototype.__one_folders) {
		Dock.prototype.__one_folders = true;
		const drawn = Dock.prototype.render_entries;
		Dock.prototype.render_entries = function (entries = this.sidebar.collect_dock_entries(this.app)) {
			const app = onedesk.rail.app();
			if (!app || this.app?.app_name !== app.app_name) return drawn.call(this, entries);
			const laid = onedesk.rail.laid(entries);
			drawn.call(this, laid.filter((one) => one.entry).map((one) => one.entry));
			let at = 0;
			for (const one of laid) {
				if (one.entry) {
					at += 1;
					continue;
				}
				const $folder = onedesk.rail.tile(this, one.folder, one.entries);
				const $after = this.$items.children(".dock-item").eq(at);
				if ($after.length) $folder.insertBefore($after);
				else this.$items.append($folder);
				at += 1;
			}
		};
	}
}

$(document).on("page-change", () => setTimeout(() => onedesk.rail.seen(), 300));
