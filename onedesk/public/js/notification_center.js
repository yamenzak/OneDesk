// NotificationCenter (docs/READY.md, mechanism 15): what each module sends
// (one/notification_center.py). A module's part, from Notifications in its
// ControlCenter, is Yours (Email and Push for each type the reader gets)
// and, for administrators, Workspace (Send This, and for each channel
// whether it is allowed and on to start with). The whole, from the bell's
// gear, Settings › You › Notifications and the arrows, starts with
// Everything (notifications and their email on or off, push in this
// browser), then each module, then Across One for what no module sends.
frappe.provide("onedesk.notification_center");

onedesk.notification_center.open = async ({ module = null, at = null } = {}) => {
	const N = "onedesk.one.notification_center.";
	const kit = onedesk.module_settings.kit;
	const esc = frappe.utils.escape_html;
	const admin = !!frappe.boot.one_administers;
	const modules = module ? [module] : (frappe.boot.one_centers || {}).notifications || [];

	// A switch at a row's end, saved as it changes; put back if refused.
	const toggle = ($end, { value, label, disabled = false, change }) => {
		const control = frappe.ui.form.make_control({
			df: { fieldtype: "Switch", fieldname: "on", label: "" },
			parent: $(`<span class="one-set-switch"></span>`).appendTo($end),
			render_input: true,
		});
		control.set_value(value ? 1 : 0);
		control.$input.attr("aria-label", label).prop("disabled", disabled);
		control.$input.on("change", async () => {
			const on = control.get_value() ? 1 : 0;
			try {
				await change(on);
				kit.saved();
			} catch (e) {
				control.set_value(on ? 0 : 1);
			}
		});
		return control;
	};
	const mark = (app) => onedesk.brand.mark_of(app.replace(/^One/, "")) || "bell";
	const pad = `<span class="one-notify-pad"></span>`;
	const columns = (words, padded = false) =>
		`<div class="one-notify-columns">${words.map((word) => `<span>${esc(word)}</span>`).join("")}${padded ? pad : ""}</div>`;

	// The reader's own: Email and Push for each type of one module, or of
	// what no module sends ("").
	const yours_tab = (app) => ({
		id: `yours:${app}`,
		label: app ? (module ? __("Yours") : app) : __("Across One"),
		icon: module ? "user" : null,
		icon_html: module || !app ? null : frappe.utils.icon(mark(app), "sm"),
		title: app ? (module ? __("Yours") : app) : __("Across One"),
		description: app ? __("What {0} tells you, and how.", [app]) : __("What the workspace's own rules and One itself tell you."),
		async render(panel) {
			const said = await frappe.xcall(N + "yours", { module: app }, "GET");
			const $body = panel.body.empty();
			const types = said.types.filter((one) => one.app === app);
			if (!said.enabled) $body.append(frappe.ui.alert.html({ title: __("Your notifications are off."), theme: "orange" }));
			if (!types.length) return $body.append(kit.empty(__("Nothing to choose here.")));
			$body.append(columns([__("Email"), __("Push")]));
			const $list = $(`<div class="one-set-list one-notify-list"></div>`).appendTo($body);
			for (const one of types) {
				const $row = kit.row({ lead: kit.glyph("bell"), title: one.label, sub: esc([one.about, one.why].filter(Boolean).join(" ")) }).appendTo($list);
				if (one.oneai) $row.find(".one-set-title").append(" ", onedesk.oneai.tag(__("OneAI")));
				const $end = $row.find(".one-set-end");
				for (const channel of ["email", "push"]) {
					toggle($end, {
						value: one[channel],
						label: `${channel === "email" ? __("Email") : __("Push")}: ${one.label}`,
						disabled: !one[`may_${channel}`] || (channel === "email" && !said.email),
						change: (on) => frappe.xcall(N + "choose", { name: one.name, channel, on }),
					});
				}
			}
		},
	});

	// The workspace's: for each type a module sends, Send This, then email
	// and push each allowed or not and on to start with or not.
	const workspace_tab = (app) => ({
		id: `workspace:${app}`,
		label: module ? __("Workspace") : app,
		icon: module ? "building" : null,
		icon_html: module ? null : frappe.utils.icon(mark(app), "sm"),
		title: module ? __("Workspace") : app,
		description: __("What {0} sends in this workspace, and the channels people may choose.", [app]),
		async render(panel) {
			const types = await frappe.xcall(N + "workspace", { module: app }, "GET");
			const $body = panel.body.empty();
			if (!types.length) return $body.append(kit.empty(__("Nothing to set here.")));
			$body.append(columns([__("Send"), __("Email"), __("Start On"), __("Push"), __("Start On")], true));
			const $list = $(`<div class="one-set-list one-notify-list one-notify-wide"></div>`).appendTo($body);
			const set = (one, field, on) => frappe.xcall(N + "set_type", { name: one.name, field, value: on }).then(() => (one[field] = on));
			for (const one of types) {
				const sub = [one.about, one.to && __("To {0}", [one.to])].filter(Boolean).join(" ");
				const $row = kit.row({ lead: kit.glyph("bell"), title: one.label, sub: esc(sub) }).appendTo($list);
				const $end = $row.find(".one-set-end");
				toggle($end, { value: one.enabled, label: `${__("Send")}: ${one.label}`, disabled: !!one.fixed, change: (on) => set(one, "enabled", on) });
				for (const field of ["one_allow_email", "one_email_default", "one_allow_push", "one_push_default"]) {
					const email = field.includes("email");
					toggle($end, {
						value: one[field],
						label: `${email ? __("Email") : __("Push")}: ${one.label}`,
						disabled: !one.channels || (email && !!one.always),
						change: (on) => set(one, field, on),
					});
				}
				if (one.words) {
					kit.button({ variant: "ghost", icon: "pencil", title: __("Edit Words"), attrs: { "aria-label": __("Edit Words") } })
						.on("click", () => {
							dialog.hide();
							frappe.set_route("one", "workspace-settings", { section: "notification_types", type: one.name });
						})
						.appendTo($end);
				} else $end.append(pad);
			}
		},
	});

	// The reader's switches over everything, and push in this browser.
	const everything = {
		id: "everything",
		label: __("Everything"),
		icon: "bell-ring",
		title: __("Everything"),
		description: __("All notifications appear in One."),
		async render(panel) {
			const said = await frappe.xcall(N + "yours", { module: "" }, "GET");
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			for (const [field, title, sub] of [
				["enabled", __("Notifications"), __("Turn off to stop all notifications.")],
				["email", __("Also by Email"), __("Emails you the notifications turned on for email.")],
			]) {
				const $row = kit.row({ lead: kit.glyph(field === "email" ? "mail" : "bell"), title, sub: esc(sub) }).appendTo($list);
				toggle($row.find(".one-set-end"), {
					value: said[field],
					label: title,
					change: (on) => frappe.xcall(N + "switch", { field: field === "email" ? "enable_email_notifications" : "enabled", on }),
				});
			}
			push($list);
		},
	};

	const push = async ($list) => {
		await frappe.require("/assets/onedesk/js/push.js");
		const here = await onedesk.push.state();
		const [label, theme] = {
			on: [__("On in this browser"), "green"],
			off: [__("Off in this browser"), "gray"],
			blocked: [__("Blocked in this browser"), "orange"],
			unsupported: [__("Not supported in this browser"), "gray"],
		}[here.state];
		const sub = here.state === "blocked" ? esc(__("Allow notifications for this site in your browser settings.")) : frappe.ui.badge.html({ label, theme });
		const $row = kit.row({ lead: kit.glyph("smartphone"), title: __("Push"), sub }).appendTo($list);
		const again = () => {
			$row.remove();
			push($list);
		};
		const $end = $row.find(".one-set-end");
		if (here.state === "off") {
			kit.button({ label: __("Turn On Push"), variant: "outline" })
				.on("click", async () => {
					const said = await frappe.xcall("onedesk.one.push.devices");
					let on = false;
					try {
						on = await onedesk.push.on(said.key);
					} catch (e) {
						on = false;
					}
					if (!on) frappe.show_alert({ message: __("Couldn't turn on push. Private windows don't support it."), indicator: "orange" });
					again();
				})
				.appendTo($end);
		} else if (here.state === "on") {
			kit.button({ label: __("Send Test"), variant: "outline" })
				.on("click", async () => {
					const said = await frappe.xcall("onedesk.one.push.test");
					frappe.show_alert({ message: said.sent ? __("Test sent") : __("Couldn't send test"), indicator: said.sent ? "green" : "orange" });
				})
				.appendTo($end);
			kit.button({ label: __("Turn Off"), variant: "ghost" })
				.on("click", async () => {
					await onedesk.push.off();
					again();
				})
				.appendTo($end);
		}
	};

	const tabs = module
		? [{ items: [yours_tab(module), ...(admin ? [workspace_tab(module)] : [])] }]
		: [
				{ items: [everything] },
				{ group: __("Yours"), items: [...modules.map(yours_tab), yours_tab("")] },
				...(admin ? [{ group: __("Workspace"), items: modules.map(workspace_tab) }] : []),
		  ];
	const ids = tabs.flatMap((group) => group.items.map((item) => item.id));
	const dialog = new onedesk.module_settings.Dialog({
		title: "NotificationCenter",
		module,
		center: "notifications",
		tabs,
		default_tab: ids.includes(at) ? at : ids[0],
		expand: module
			? () => {
					dialog.hide();
					onedesk.notification_center.open();
			  }
			: null,
	});
	dialog.$wrapper.addClass("one-set one-notify");
	dialog.show();
	return dialog;
};
