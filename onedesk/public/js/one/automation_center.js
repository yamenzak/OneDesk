// AutomationCenter (docs/ARC-AI.md, AutomationCenter; one/automation_center.py):
// every automation the reader keeps or asks for, a section for each place
// one runs (a mailbox, a channel), grouped by what starts it. A place lists its
// automations in the order they run; opening one, or New Automation, draws
// its builder, the island onedesk.automation (frontend/src/automation/), on
// frappe's own flow canvas. Save, Send Request, Approve, Decline and Delete
// are the view's own buttons; each goes through the trigger's app, which
// says who changes, who asks and who approves.
onedesk.centers.declare("automation", {
	help: [onedesk.names.of("one_mail"), "rules-and-out-of-office"],
	whose: () => ({ key: "automation", label: __("Your Workspace"), icon: "building" }),
	async sections(ctx) {
		const C = "onedesk.one.automation_center.";
		const kit = onedesk.centers.kit;
		const esc = frappe.utils.escape_html;
		const places = await frappe.xcall(C + "places", {}, "GET");

		// One automation in its builder, on a view of the place's section.
		const builder = (panel, place, scope, automation = null) => {
			let value = null;
			let island = null;
			const asking = !scope.manages;
			const done = () => {
				island?.unmount();
				kit.saved();
				panel.refresh();
			};
			const save = async () => {
				if (!value) return;
				await frappe.xcall(C + "save", { trigger: place.trigger, scope: scope.scope, values: value, name: automation ? automation.name : null });
				done();
			};
			const decide = (approve) => async () => {
				await frappe.xcall(C + "decide", { name: automation.name, approve: approve ? 1 : 0 });
				done();
			};
			const actions = [{ label: asking ? __("Send Request") : __("Save"), variant: "solid", click: save }];
			if (automation && automation.requested_by && scope.manages) {
				actions.splice(0, 1, { label: __("Decline"), theme: "red", click: decide(false) }, { label: __("Approve"), variant: "solid", click: decide(true) });
			}
			if (automation && (asking ? automation.requested_by : !automation.requested_by)) {
				actions.unshift({
					label: __("Delete"),
					theme: "red",
					click: () =>
						frappe.confirm(__("Delete this automation?"), async () => {
							await frappe.xcall(C + "delete", { name: automation.name });
							done();
						}),
				});
			}
			kit.view(panel, {
				title: automation ? automation.title || __("Automation") : asking ? __("Request Automation") : __("New Automation"),
				description:
					automation && automation.requested_by
						? __("{0} asked for this automation, which runs once approved.", [automation.requested_by_name || automation.requested_by])
						: undefined,
				actions,
				/** frappe's flow canvas and the chosen step's settings, an island: steps that branch are a flow a list cannot draw. */
				render: (shown) => {
					const $host = $(`<div class="one-automation-builder"></div>`).appendTo(shown.body);
					island = frappe.ui.mount_island("onedesk.automation", $host[0], {
						trigger: place.trigger,
						scope: scope.scope,
						automation: automation ? automation.name : null,
						onChange: (said) => (value = said),
					});
				},
			});
		};

		// A place's automations in the order they run, each opening its builder.
		const section = (place, scope) => ({
			id: `${place.trigger}:${scope.scope}`,
			label: scope.label,
			icon: place.icon,
			title: scope.label,
			description: scope.manages ? place.runs : __("Run in order on each new message once a Mail Manager approves them."),
			count: scope.count || null,
			actions: [{ label: scope.manages ? __("New Automation") : __("Request Automation"), icon: "plus", click: (panel) => builder(panel, place, scope) }],
			/** The place's automations, each a row opening its builder, with its switch or what it waits for: rows that open views of their own. */
			async render(panel) {
				const was = panel.shown;
				const said = await frappe.xcall(C + "automations", { trigger: place.trigger, scope: scope.scope }, "GET");
				if (panel.shown !== was || !said.may) return;
				const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
				if (!said.rules.length) kit.nothing(panel.body, __("No automations yet"), "workflow");
				for (const one of said.rules) {
					const $end = kit
						.row({
							lead: kit.glyph(one.needs_ai ? "oneai" : "workflow"),
							title: one.title || __("Automation"),
							sub: esc([one.when, one.then].filter(Boolean).join(" → ")),
							end: kit.chevron(),
							open: () => builder(panel, place, scope, one),
						})
						.appendTo($list)
						.find(".one-set-end");
					if (one.requested_by) {
						$end.prepend(frappe.ui.badge.html({ label: __("Waiting for Approval"), theme: "amber" }));
						continue;
					}
					if (one.needs_ai && one.enabled && !said.reads) $end.prepend(frappe.ui.badge.html({ label: __("Not Running"), theme: "gray" }));
					if (!said.manages) continue;
					const on = frappe.ui.form.make_control({
						df: { fieldtype: "Switch", fieldname: "enabled", label: "" },
						parent: $(`<span class="one-set-switch"></span>`).prependTo($end),
						render_input: true,
					});
					on.set_value(one.enabled ? 1 : 0);
					on.$input.attr("aria-label", __("Enabled")).on("change", async () => {
						await frappe.xcall(C + "enable", { name: one.name, enabled: on.get_value() ? 1 : 0 });
						kit.saved();
					});
				}
				const asked = ctx.record && said.rules.find((one) => one.name === ctx.record);
				if (asked) {
					ctx.record = null;
					builder(panel, place, scope, asked);
				}
			},
		});

		if (!places.length) {
			return [
				{
					group: null,
					items: [{ id: "none", label: __("Automations"), icon: "workflow", title: __("Automations"), rows: async () => [], empty: __("Nothing here runs by itself for you yet.") }],
				},
			];
		}
		return places.map((place) => ({ group: place.label, items: place.scopes.map((scope) => section(place, scope)) }));
	},
});
