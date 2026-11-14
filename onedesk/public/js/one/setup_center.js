// SetupCenter (one/setup_center.py): every app's setup steps, done and
// waiting. Overview lists each app that has steps; each app's section lists
// its steps, a step with fields as the wizard's own form, one without
// opening the section that does it; Ask puts the step to SetupCenter's
// setup guide in OneAI's panel (one/setup_center_agent.py). `at` opens one
// app, as Apps does after Install.
onedesk.centers.declare("setup", {
	help: ["One", "setup"],
	css: "one-setup",
	async sections(ctx) {
		const S = "onedesk.one.setup_center.";
		const kit = onedesk.centers.kit;
		const esc = frappe.utils.escape_html;
		let apps = (await frappe.xcall(S + "load")).apps;
		const of = (app) => apps.find((one) => one.app === app) || { steps: [], waiting: 0 };
		const kept = (said) => {
			apps = said.apps;
			frappe.boot.one_setup = Object.fromEntries(apps.map((one) => [one.app, one.steps]));
		};
		const state = (one) =>
			one.waiting
				? frappe.ui.badge.html({ label: __("{0} Waiting", [one.waiting]), theme: "amber" })
				: frappe.ui.badge.html({ label: __("Done"), theme: "green" });

		const opens = (one, step) => {
			ctx.centre.hide();
			if (one.center === "settings") onedesk.centers.open("settings", { module: one.app, at: step.tab });
			else onedesk.centers.open(one.center, { at: step.tab });
		};

		const form = ($into, one, step, panel) => {
			const $form = $(`<div class="one-setup-form"></div>`).appendTo($into);
			const group = kit.fields($form, step.fields);
			const $buttons = kit.buttons($form);
			kit.button({ label: __("Save"), variant: "solid" })
				.on("click", async () => {
					const values = group.get_values();
					if (!values) return;
					kept(await frappe.xcall(S + "save", { module: one.app, key: step.key, values }));
					kit.saved();
					panel.refresh();
				})
				.appendTo($buttons);
			kit.button({ label: __("Cancel"), variant: "ghost" }).on("click", () => $form.remove()).appendTo($buttons);
		};

		const steps = (app, panel) => {
			const one = of(app);
			const $list = $(`<div class="one-set-list one-set-steps"></div>`).appendTo(panel.body.empty());
			for (const step of one.steps) {
				const $row = kit.row({ lead: kit.glyph(step.done ? "circle-check" : "circle"), title: step.title, sub: esc(step.about) }).appendTo($list);
				const $end = $(`<span class="one-set-buttons"></span>`).appendTo($row.find(".one-set-end"));
				if (step.done) {
					$end.append(frappe.ui.badge.html({ label: __("Done"), theme: "green" }));
					continue;
				}
				kit.button({ label: __("Set Up"), variant: "solid" })
					.on("click", () => {
						if (!step.fields.length) return opens(one, step);
						if (!$row.next(".one-setup-form").length) form($(`<div></div>`).insertAfter($row), one, step, panel);
					})
					.appendTo($end);
				kit.button({ label: __("Mark as Done"), variant: "ghost" })
					.on("click", async () => {
						kept(await frappe.xcall(S + "finish", { module: one.app, key: step.key }));
						panel.refresh();
					})
					.appendTo($end);
				if (onedesk.apps.ai())
					kit.button({ label: __("Ask", null, "Ask a question"), variant: "ghost" })
						.on("click", () => onedesk.oneai.open({ ask: __("What does {0} set up, and what should we answer?", [step.title]) }))
						.appendTo($end);
			}
			if (!one.steps.length) $list.append(kit.empty(__("Nothing to set up.")));
		};

		const overview = {
			id: "overview",
			label: __("Overview"),
			icon: "list-checks",
			title: __("Overview"),
			description: __("What each app needs set up so it works the way your company does."),
			empty: __("Nothing to set up."),
			rows: () =>
				apps.map((one) => ({
					lead: onedesk.centers.app_icon(one.app, "list-checks"),
					title: one.app,
					sub: esc(__("{0} of {1} done", [one.steps.length - one.waiting, one.steps.length])),
					end: state(one),
					open: () => ctx.centre.activate(one.app),
				})),
		};
		const app_tab = (one) => ({
			id: one.app,
			label: one.app,
			icon_html: onedesk.centers.app_icon(one.app, "list-checks"),
			title: one.app,
			description: __("What to set up so {0} works the way your company does.", [one.app]),
			/** Set Up opens a step's form in place, under the step, and Mark as
			 * Done changes its row: rows with forms between them, which no
			 * declared kind draws. */
			render: (panel) => steps(one.app, panel),
		});

		const order = {
			id: "order",
			label: __("Order of Apps"),
			icon: "arrow-up-down",
			title: __("Order of Apps"),
			description: __("The order of the apps on the rail for everybody who has not arranged their own."),
			/** A list dragged into order with Save and Reset under it, which
			 * no declared kind draws. */
			render: async (panel) => {
				const R = "onedesk.one.rail.";
				const draw = ({ apps: shown }) => {
					panel.body.empty();
					const read = onedesk.rail.sortable(panel.body, shown.map((one) => ({ key: one.key, label: one.title, icon: one.icon })));
					const $buttons = kit.buttons(panel.body);
					kit.button({ label: __("Save"), variant: "solid" })
						.on("click", async () => {
							draw(await frappe.xcall(R + "save_workspace", { order: read() }));
							kit.saved(__("Order of Apps"));
						})
						.appendTo($buttons);
					kit.button({ label: __("Reset"), variant: "ghost" })
						.on("click", async () => {
							draw(await frappe.xcall(R + "save_workspace", { order: [] }));
							kit.saved(__("Order of Apps"));
						})
						.appendTo($buttons);
				};
				draw(await frappe.xcall(R + "workspace"));
			},
		};

		return [
			{ items: [overview] },
			...(apps.length ? [{ group: __("Apps"), items: apps.map(app_tab) }] : []),
			...(frappe.boot.one_administers ? [{ group: __("Workspace"), items: [order] }] : []),
		];
	},
});
