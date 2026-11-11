frappe.provide("onedesk.interface");

onedesk.interface.views = {
	of(doctype) {
		return frappe.boot.one_interface?.[doctype]?.views || [];
	},

	all() {
		return Object.values(frappe.boot.one_interface || {}).flatMap((one) => one.views || []);
	},

	made(name) {
		const views = this;
		return class extends frappe.views.ListView {
			static no_sidebar = true;

			get view_name() {
				return name;
			}

			get show_saved_layout_menu() {
				return false;
			}

			setup_page() {
				this.one_view = views.of(this.doctype).find((one) => one.name === name);
				this.hide_page_form = true;
				this.hide_filters = true;
				this.hide_sort_selector = true;
				super.setup_page();
			}

			setup_view() {
				if (!this.one_view) return frappe.set_route("List", this.doctype, "List");
				if (this.one_island) return;
				const $body = $('<div class="one-island"></div>');
				this.$frappe_list.empty().append($body);
				this.one_island = frappe.ui.mount_island(this.one_view.island, $body[0], { doctype: this.doctype, win: this.page.interface || null });
				this.one_island.ready.catch((error) => {
					console.error(`could not mount the "${this.one_view.island}" island`, error);
					$body.html(frappe.ui.empty_state.html({ icon: this.one_view.icon, title: __("This view is not built"), description: frappe.boot.developer_mode ? error.message : "" }));
				});
				this.settings.onload && this.settings.onload(this);
			}

			make_new_doc() {
				frappe.new_doc(this.doctype);
			}

			refresh() {
				return Promise.resolve();
			}

			render() {}
		};
	},

	setup() {
		const views = this;
		const declared = this.all().filter((one) => !frappe.views[`${one.name}View`]);
		if (!declared.length) return;
		const labels = frappe.views.get_view_label_map;
		frappe.views.get_view_label_map = () => ({ ...labels(), ...Object.fromEntries(views.all().map((one) => [one.name, __(one.label)])) });
		declared.forEach((one) => {
			if (!frappe.views.view_modes.includes(one.name)) frappe.views.view_modes.push(one.name);
			frappe.views.view_icon_map[one.name] ||= one.icon;
			frappe.router.list_views_route[one.name.toLowerCase()] = one.name;
			frappe.views[`${one.name}View`] = views.made(one.name);
		});
		onedesk.interface.when(frappe.views, "ListViewSelect", (Select) => {
			if (Object.hasOwn(Select.prototype, "one_views")) return;
			Select.prototype.one_views = true;
			const offered = Select.prototype.get_views;
			Select.prototype.get_views = function () {
				const said = offered.call(this);
				const own = views.of(this.doctype).map((one) => one.name);
				declared.forEach((one) => {
					said[one.name] = { condition: own.includes(one.name), action: () => this.set_route(one.name.toLowerCase()) };
				});
				return said;
			};
		});
	},
};

onedesk.interface.views.setup();
