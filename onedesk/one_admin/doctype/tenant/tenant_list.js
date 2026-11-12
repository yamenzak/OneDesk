frappe.listview_settings["Tenant"] = {
	add_fields: ["status", "storage_bytes", "storage_limit", "domain", "is_house", "is_test"],
	hide_name_column: true,
	hide_name_filter: true,

	get_indicator(doc) {
		if (doc.is_house) return [__("Internal"), "blue", "is_house,=,1"];
		if (doc.is_test) return [__("Test"), "violet", "is_test,=,1"];
		const says = {
			Requested: ["orange", __("Waiting to be built")],
			Provisioning: ["blue", __("Being built")],
			Live: ["green", __("Live")],
			Overdue: ["orange", __("Payment overdue")],
			Suspended: ["red", __("Suspended")],
			Archived: ["grey", __("Archived")],
			Dropped: ["grey", __("Dropped")],
			Failed: ["red", __("Provisioning failed")],
		};
		const [colour, word] = says[doc.status] || ["grey", doc.status];
		return [word, colour, `status,=,${doc.status}`];
	},

	onload(listview) {
		listview.page.add_menu_item(__("New Test Workspace"), () => {
			frappe.prompt(
				[
					{ fieldname: "address", fieldtype: "Data", label: __("Site Address"), reqd: 1 },
					{ fieldname: "workspace_name", fieldtype: "Data", label: __("Workspace Name"), reqd: 1 },
				],
				async (values) => {
					const said = await frappe.xcall("onedesk.one_admin.testbed.new", values);
					const config = JSON.stringify(said.config, null, 1);
					listview.refresh();
					const shown = new frappe.ui.Dialog({
						title: __("Link {0}", [said.tenant]),
						fields: [
							{
								fieldname: "config",
								fieldtype: "Code",
								label: __("Site Config"),
								read_only: 1,
								default: config,
								description: __("Shown only once, for deploy/local/link.sh on the machine that serves the site."),
							},
						],
						primary_action_label: __("Copy Site Config"),
						primary_action() {
							frappe.utils.copy_to_clipboard(config);
							shown.hide();
						},
					});
					shown.show();
				},
				__("New Test Workspace"),
				__("Create"),
			);
		});
	},

	formatters: {
		workspace_name(value, df, doc) {
			return value && value !== doc.name ? `${value} · ${doc.name}` : doc.name;
		},
		storage_bytes(value, df, doc) {
			const held = Number(value || 0) ? onedesk.tenant.size(value) : "0";
			if (!doc.storage_limit) return held;
			const said = __("{0} of {1}", [held, onedesk.tenant.size(doc.storage_limit)]);
			const over = Number(value || 0) > Number(doc.storage_limit);
			return over ? `<span class="text-danger">${said}</span>` : said;
		},
	},
};
