frappe.provide("onedesk.apps");

onedesk.apps.hidden = () => new Set(frappe.boot.one_hidden?.doctypes || []);
onedesk.apps.ai = () => frappe.boot.one_hidden?.ai !== false;
onedesk.apps.intake = () => frappe.boot.one_hidden?.intake !== false;

onedesk.apps.button = ($dock) => {
	const $user = $dock.find(".dock-user");
	if (!$user.length || $dock.find(".one-apps-button").length) return;
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
		onedesk.rail.launcher();
	});
	onedesk.interface.tips.name($button[0], __("Apps"));
};

onedesk.apps.card = (app, titles) => {
	const esc = frappe.utils.escape_html;
	const needs = app.needs || [];
	const states = { Installing: __("Installing…"), Failed: __("Couldn't be installed. We've been told.") };
	const tag = app.kept ? (app.state ? states[app.state] || app.state : __("Private app")) : "";
	return `<button type="button" class="one-app-card ${app.on ? "" : "is-off"} ${app.held ? "is-locked is-held" : ""} ${app.kept ? "is-kept" : ""}" data-app="${esc(
		app.name
	)}" data-needs="${esc(needs.join("|"))}" ${app.section ? 'data-section="1"' : ""} aria-pressed="${app.on}" ${app.held || app.kept ? "disabled" : ""}>
		<span class="one-app-top">
			<span class="one-app-icon">${frappe.utils.icon(app.icon, "xl")}</span>
			${app.kept ? `<span class="one-app-tag">${esc(tag)}</span>` : `<span class="one-app-switch"></span>`}
		</span>
		<span class="one-app-name">${esc(app.title)}</span>
		<span class="one-app-said">${esc(app.said)}</span>
		${needs.length ? `<span class="one-app-needs">${esc(__("Needs {0}", [needs.map((one) => titles[one] || one).join(", ")]))}</span>` : ""}
		<span class="one-app-held">${esc(app.held || "")}</span>
	</button>`;
};

/** Each card an app left on needs can't be turned off, and says which. */
onedesk.apps.lock = ($wrapper, titles) => {
	const $cards = $wrapper.find(".one-app-card");
	const needs = (card) => ($(card).attr("data-needs") || "").split("|").filter(Boolean);
	$cards.not(".is-held").each((_i, card) => {
		const name = $(card).attr("data-app");
		const by = $cards
			.filter((_j, other) => !$(other).hasClass("is-off") && !$(other).is("[data-section]") && needs(other).includes(name))
			.map((_j, other) => titles[$(other).attr("data-app")] || $(other).attr("data-app"))
			.get();
		const locked = by.length > 0 && !$(card).hasClass("is-off");
		$(card).toggleClass("is-locked", locked);
		if (!$(card).hasClass("is-kept")) $(card).prop("disabled", locked);
		$(card).find(".one-app-held").text(locked ? __("Needed by {0}", [by.join(", ")]) : "");
	});
};

onedesk.apps.configure = async () => {
	const { apps } = await frappe.xcall("onedesk.one.apps.read");
	const titles = Object.fromEntries(apps.map((app) => [app.name, app.title]));
	const dialog = new frappe.ui.Dialog({
		title: __("Turn Apps On or Off"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "apps",
				options: `<p class="one-apps-said">${__(
					"An app turned off leaves the rail and search for everybody. Its records stay, and links to them still open."
				)}</p><div class="one-apps-grid">${apps.map((app) => onedesk.apps.card(app, titles)).join("")}</div>`,
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
			const { said } = await frappe.xcall("onedesk.one.apps.save", { off });
			dialog.hide();
			// An app turned on that has steps opens in SetupCenter, on its steps.
			const landed = apps.find((app) => !app.on && !off.includes(app.name) && ((frappe.boot.one_setup || {})[app.name] || []).length);
			const go = () => (landed ? window.location.assign(`/desk/one?center=setup&at=${encodeURIComponent(landed.name)}`) : window.location.reload());
			if (!said?.length) {
				frappe.show_alert({ message: __("Apps saved"), indicator: "green" });
				return go();
			}
			frappe.msgprint({ title: __("Apps saved"), message: said.map(frappe.utils.escape_html).join("<br>") }).onhide = go;
		},
	});
	const set = ($card, on) => $card.toggleClass("is-off", !on).attr("aria-pressed", on);
	dialog.$wrapper.on("click", "[data-claim]", async () => {
		const $input = dialog.$wrapper.find(".one-apps-code input");
		const code = ($input.val() || "").trim();
		if (!code) return $input.trigger("focus");
		const app = await frappe.xcall("onedesk.account_center.private.claim", { code });
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
	dialog.$wrapper.on("click", ".one-app-card:not(.is-kept):not(.is-locked)", (event) => {
		const $card = $(event.currentTarget);
		const on = $card.hasClass("is-off");
		set($card, on);
		const bring = (card) =>
			($(card).attr("data-needs") || "")
				.split("|")
				.filter(Boolean)
				.forEach((name) => {
					const $needed = dialog.$wrapper.find(".one-app-card.is-off").filter((_i, one) => $(one).attr("data-app") === name);
					set($needed, true);
					$needed.each((_i, one) => bring(one));
				});
		if (on) bring($card[0]);
		else set(dialog.$wrapper.find(".one-app-card[data-section]").filter((_i, one) => ($(one).attr("data-needs") || "").split("|").includes($card.attr("data-app"))), false);
		onedesk.apps.lock(dialog.$wrapper, titles);
	});
	onedesk.apps.lock(dialog.$wrapper, titles);
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
