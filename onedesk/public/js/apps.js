frappe.provide("onedesk.apps");

onedesk.apps.hidden = () => new Set(frappe.boot.one_hidden?.doctypes || []);
onedesk.apps.ai = () => frappe.boot.one_hidden?.ai !== false;
onedesk.apps.intake = () => frappe.boot.one_hidden?.intake !== false;

onedesk.apps.button = ($dock) => {
	const $user = $dock.find(".dock-user");
	if (!$user.length || $dock.find(".one-apps-button").length) return;
	if (!frappe.user.has_role("Workspace Administrator")) return;
	const $button = $(
		`<div class="one-apps"><button class="dock-item one-apps-button" aria-label="${__("Apps")}">${frappe.utils.icon(
			"layout-grid",
			"md"
		)}</button></div>`
	)
		.insertBefore($user)
		.find("button");
	$button.on("click", (event) => {
		event.stopPropagation();
		onedesk.apps.configure();
	});
	onedesk.interface.tips.name($button[0], __("Apps"));
};

onedesk.apps.card = (app, off) => {
	const esc = frappe.utils.escape_html;
	const locked = app.needs && off.has(app.needs);
	const states = { Installing: __("Installing…"), Failed: __("Couldn't be installed. We've been told.") };
	const tag = app.kept ? (app.state ? states[app.state] || app.state : __("Private app")) : "";
	return `<button type="button" class="one-app-card ${app.on ? "" : "is-off"} ${locked ? "is-locked" : ""} ${app.kept ? "is-kept" : ""}" data-app="${esc(
		app.name
	)}" data-needs="${esc(app.needs || "")}" aria-pressed="${app.on}" ${locked || app.kept ? "disabled" : ""}>
		<span class="one-app-top">
			<span class="one-app-icon">${frappe.utils.icon(app.icon, "xl")}</span>
			${app.kept ? `<span class="one-app-tag">${esc(tag)}</span>` : `<span class="one-app-switch"></span>`}
		</span>
		<span class="one-app-name">${esc(app.title)}</span>
		<span class="one-app-said">${esc(app.said)}</span>
		${app.needs ? `<span class="one-app-needs">${esc(__("Needs {0}", [app.needs]))}</span>` : ""}
	</button>`;
};

onedesk.apps.configure = async () => {
	const { apps } = await frappe.xcall("onedesk.one.apps.read");
	const off = new Set(apps.filter((app) => !app.on).map((app) => app.name));
	const dialog = new frappe.ui.Dialog({
		title: __("Apps"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "apps",
				options: `<p class="one-apps-said">${__(
					"An app turned off leaves the rail and search for everybody. Its records stay, and links to them still open."
				)}</p><div class="one-apps-grid">${apps.map((app) => onedesk.apps.card(app, off)).join("")}</div>`,
			},
			{
				fieldtype: "HTML",
				fieldname: "code",
				options: `<div class="one-apps-code"><span class="one-apps-said">${__(
					"Have a code for a private app? Type it here. Once installed, a private app stays on."
				)}</span><span class="one-apps-code-field"><input type="text" class="form-control" autocomplete="off" spellcheck="false" aria-label="${__(
					"Code"
				)}" placeholder="XXXX-XXXX-XXXX">${frappe.ui.button.html({ label: __("Add"), variant: "subtle", attrs: { "data-claim": "1" } })}</span></div>`,
			},
		],
		primary_action_label: __("Save"),
		primary_action: async () => {
			const off = dialog.$wrapper
				.find(".one-app-card.is-off:not(.is-kept)")
				.map((_i, card) => $(card).attr("data-app"))
				.get();
			await frappe.xcall("onedesk.one.apps.save", { off });
			dialog.hide();
			frappe.show_alert({ message: __("Apps saved"), indicator: "green" });
			window.location.reload();
		},
	});
	const set = ($card, on) => $card.toggleClass("is-off", !on).attr("aria-pressed", on);
	dialog.$wrapper.on("click", "[data-claim]", async () => {
		const $input = dialog.$wrapper.find(".one-apps-code input");
		const code = ($input.val() || "").trim();
		if (!code) return $input.trigger("focus");
		const app = await frappe.xcall("onedesk.one_account.private.claim", { code });
		dialog.hide();
		frappe.msgprint({
			title: app.title,
			message:
				app.state === "Installed"
					? __("{0} is already installed.", [frappe.utils.escape_html(app.title)])
					: __("{0} is being installed. It takes a few minutes, and appears in Apps and on the rail when it's ready.", [
							frappe.utils.escape_html(app.title),
					  ]),
		});
	});
	dialog.$wrapper.on("click", ".one-app-card:not(.is-kept)", (event) => {
		const $card = $(event.currentTarget);
		const on = $card.hasClass("is-off");
		set($card, on);
		const $needing = dialog.$wrapper.find(`.one-app-card[data-needs="${$card.attr("data-app")}"]`);
		if (!on) set($needing, false);
		$needing.toggleClass("is-locked", !on).prop("disabled", !on);
	});
	dialog.show();
};

if (frappe.search?.AwesomeBar) {
	const build = frappe.search.AwesomeBar.prototype.build_options;
	frappe.search.AwesomeBar.prototype.build_options = function (txt) {
		const hidden = onedesk.apps.hidden();
		const found = build.call(this, txt);
		if (!hidden.size) return found;
		return found.filter((one) => !(one.route && hidden.has(one.route[1])));
	};
}

frappe.ui.form.on("*", {
	refresh(frm) {
		const hidden = onedesk.apps.hidden();
		if (!hidden.size) return;
		for (const df of frm.meta.fields) {
			if (df.fieldtype !== "Link" || !hidden.has(df.options) || df.hidden) continue;
			frm.toggle_display(df.fieldname, !!frm.doc[df.fieldname]);
		}
	},
});

if (frappe.ui.Dock) {
	const make = frappe.ui.Dock.prototype.make;
	frappe.ui.Dock.prototype.make = function () {
		make.call(this);
		onedesk.apps.button(this.$dock);
	};
}

$(document).on("app_ready", () => {
	onedesk.apps.button($("#desk-dock"));
	frappe.realtime.on("one_apps", () =>
		frappe.show_alert({ message: __("The workspace's apps changed. Reload to see them."), indicator: "blue" }, 10)
	);
});
