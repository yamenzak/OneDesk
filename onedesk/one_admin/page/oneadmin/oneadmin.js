// OneAdmin's Home: how the workspaces stand, and what needs the operator.
//
// Both come from one_admin/home.py, for the operator only. The numbers along
// the top each open their list with the same filters they counted; Needs You
// is one list of what is stuck, owing or waiting, each saying why, with its
// one action (`operator.py`'s own verbs). Nothing here decides anything.
//
// The page is for One Operator alone (its Page roles), so the dock and the
// rail offer it to nobody else: a page's roles are not widened for Workspace
// Manager the way a workspace's are.

frappe.pages["oneadmin"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("OneAdmin"));
	wrapper.oneadmin = new onedesk.OneAdminHome(page);
};

frappe.pages["oneadmin"].on_page_show = (wrapper) => {
	wrapper.oneadmin && wrapper.oneadmin.refresh();
};

frappe.provide("onedesk");

onedesk.OneAdminHome = class OneAdminHome {
	// What needs the operator, said as one word each, in the list's badge.
	static KINDS = {
		job: ["red", __("Failed")],
		signup: ["red", __("Paid, Not Built")],
		owing: ["orange", __("Owing")],
		domain: ["orange", __("Domain")],
	};

	constructor(page) {
		this.page = page;
		page.set_secondary_action(__("Refresh"), () => this.refresh(), "refresh-cw");
		this.$body = onedesk.shell.body(page.$shell).html(`<div class="one-admin-counts"></div><div class="one-admin-needs"></div>`);
		this.$counts = this.$body.find(".one-admin-counts");
		this.$needs = this.$body.find(".one-admin-needs");
		this.$counts.on("click", "[data-count]", (e) => this.open_count($(e.currentTarget).attr("data-count")));
		this.$needs.on("click", "[data-act]", (e) => {
			// The button sits in the row's link, which would follow it too.
			e.preventDefault();
			e.stopPropagation();
			this.act($(e.currentTarget));
		});
		this.listen();
	}

	async refresh() {
		const [counts, needs] = await Promise.all([
			frappe.xcall("onedesk.one_admin.home.counts"),
			frappe.xcall("onedesk.one_admin.home.needs"),
		]);
		this.counts = counts || [];
		this.needs = needs || [];
		this.draw_counts();
		this.draw_needs();
	}

	// The numbers sit on the page, each a link to its list.
	draw_counts() {
		const esc = frappe.utils.escape_html;
		const loud = { failed: "red", signups: "red", owing: "orange" };
		this.$counts.html(
			this.counts
				.map(
					(one) => `<button class="one-admin-count" data-count="${esc(one.key)}">
						<span class="one-admin-count-value${one.value && loud[one.key] ? ` one-admin-${loud[one.key]}` : ""}">${frappe.format(one.value, { fieldtype: "Int" })}</span>
						<span class="one-admin-count-label">${esc(one.label)}</span>
					</button>`
				)
				.join("")
		);
	}

	open_count(key) {
		const one = this.counts.find((count) => count.key === key);
		if (one) frappe.set_route("List", one.doctype, one.filters);
	}

	// One list of what needs the operator, most pressing first.
	draw_needs() {
		const esc = frappe.utils.escape_html;
		if (!this.needs.length) {
			this.$needs.html(
				onedesk.shell.section(
					__("Needs You"),
					onedesk.shell.empty(__("Nothing needs you."), __("No job has failed, nobody owes, and every domain is working."), { icon: "circle-check" })
				)
			);
			return;
		}
		const rows = this.needs
			.map((one, i) => {
				const [colour, word] = OneAdminHome.KINDS[one.kind] || ["gray", one.kind];
				const action = one.action
					? frappe.ui.button.html({ label: one.action.label, size: "sm", attrs: { "data-act": i } })
					: "";
				return onedesk.shell.row({
					title: `${esc(one.title)} ${frappe.ui.badge.html({ label: word, theme: colour, size: "sm" })}`,
					sub: esc(one.why || ""),
					quiet: esc(one.detail || ""),
					meta: one.since ? esc(frappe.datetime.prettyDate(one.since)) : "",
					actions: action,
					href: `/desk/${frappe.router.slug(one.doctype)}/${encodeURIComponent(one.name)}`,
				});
			})
			.join("");
		this.$needs.html(
			onedesk.shell.section(__("Needs You"), onedesk.shell.list(rows), "", `<span class="one-shell-quiet">${this.needs.length}</span>`)
		);
	}

	// The row's one action, as operator.py does it; the list is drawn again
	// from what the server then says.
	async act($button) {
		const one = this.needs[Number($button.attr("data-act"))];
		if (!one || !one.action) return;
		$button.prop("disabled", true);
		try {
			await frappe.xcall(one.action.method, one.action.args);
			frappe.show_alert({ message: __("{0}: done.", [one.action.label]), indicator: "green" });
		} finally {
			$button.prop("disabled", false);
			this.refresh();
		}
	}

	// A job, a workspace, a signup or a domain that changes anywhere draws
	// Home again, a moment after the last change.
	listen() {
		const doctypes = ["Provisioning Job", "Tenant", "Tenant Domain", "Account Request"];
		doctypes.forEach((doctype) => frappe.realtime.doctype_subscribe(doctype));
		const again = frappe.utils.debounce(() => this.refresh(), 800);
		frappe.realtime.on("list_update", (data) => {
			if (data && doctypes.includes(data.doctype) && this.$needs.is(":visible")) again();
		});
	}
};
