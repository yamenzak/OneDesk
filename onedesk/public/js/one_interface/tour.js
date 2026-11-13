// A module's tours (one/tours.py), one for each area of its screen, each
// step at a `data-tour` mark, on frappe's driver. The area on screen is the
// first whose `at` mark is shown; its tour starts from the tour button in
// the module's foot, never by itself.
frappe.provide("onedesk.tour");

onedesk.tour.shown = (target) => {
	const el = onedesk.tour.find(target);
	return el && el.getClientRects().length ? el : null;
};

onedesk.tour.here = async (module) => {
	onedesk.tour._of = onedesk.tour._of || {};
	if (!onedesk.tour._of[module]) onedesk.tour._of[module] = frappe.xcall("onedesk.one.tours.tour", { module });
	const tours = await onedesk.tour._of[module];
	return tours.find((one) => onedesk.tour.shown(one.at));
};

onedesk.tour.run = async (module, tour = null) => {
	tour = tour || (await onedesk.tour.here(module));
	const shown = ((tour && tour.steps) || []).map((step) => ({ step, el: onedesk.tour.shown(step.target) })).filter(({ el }) => el);
	if (!shown.length) {
		frappe.show_alert({ message: __("There is no tour of this screen yet."), indicator: "blue" });
		return;
	}
	// A tour of a dialog keeps the dialog above driver's overlay, and each
	// step is outlined in it rather than lifted out of it.
	const in_dialog = shown.some(({ el }) => el.closest(".modal"));
	document.body.classList.toggle("one-tour-in-dialog", in_dialog);
	const done = () => {
		document.body.classList.remove("one-tour-in-dialog");
		const unseen = frappe.boot.one_tours_unseen || [];
		const at = unseen.indexOf(`${module}:${tour.key}`);
		if (at >= 0) unseen.splice(at, 1);
		onedesk.tour._running = false;
		frappe.xcall("onedesk.one.tours.seen", { module, key: tour.key });
	};
	onedesk.tour._running = true;
	const driver = new frappe.Driver({
		className: "frappe-driver one-tour",
		allowClose: true,
		padding: 6,
		opacity: 0.25,
		nextBtnText: __("Next"),
		prevBtnText: __("Previous"),
		doneBtnText: __("Done"),
		closeBtnText: __("Close"),
		onReset: done,
	});
	driver.defineSteps(
		shown.map(({ step, el }) => ({
			element: el,
			popover: { title: step.title, description: step.text, position: onedesk.tour.side(step.side) },
			onHighlighted: () => {
				onedesk.tour.lift(el);
				if (in_dialog) $(el).parents(".driver-fix-stacking").removeClass("driver-fix-stacking");
			},
		}))
	);
	driver.start();
};

// A step's side is written for a left-to-right page; a right-to-left one
// mirrors it, so a card set beside the rail stays on the screen.
onedesk.tour.side = (side) => {
	if (document.documentElement.dir !== "rtl") return side;
	return { left: "right", right: "left" }[side] || side;
};

// An island's parts sit in shadow roots of their own, so a mark is looked
// for in every one, and driver's highlight rules are lent to the root it is in.
onedesk.tour.find = (target, root = document) => {
	// A dialog closed earlier can still hold the same mark, so a shown one wins.
	const all = [...root.querySelectorAll(`[data-tour="${CSS.escape(target)}"]`)];
	const el = all.find((one) => one.getClientRects().length) || all[0];
	if (el) return onedesk.tour.lend(el);
	for (const host of root.querySelectorAll("*")) {
		const found = host.shadowRoot && onedesk.tour.find(target, host.shadowRoot);
		if (found) return found;
	}
};

onedesk.tour.lend = (el) => {
	const root = el.getRootNode();
	if (!(root instanceof ShadowRoot)) return el;
	if (!onedesk.tour._sheet) {
		onedesk.tour._sheet = new CSSStyleSheet();
		const rules = [...document.styleSheets].flatMap((sheet) => {
			try {
				return [...sheet.cssRules].map((rule) => rule.cssText).filter((text) => text.includes(".driver-"));
			} catch (e) {
				return [];
			}
		});
		onedesk.tour._sheet.replaceSync(rules.join("\n"));
	}
	if (!root.adoptedStyleSheets.includes(onedesk.tour._sheet))
		root.adoptedStyleSheets = [...root.adoptedStyleSheets, onedesk.tour._sheet];
	return el;
};

// Driver lifts a mark out of the layers above it, but stops at a shadow
// root; the layers outside it (the sticky command row) are lifted here.
onedesk.tour.lift = (el) => {
	for (let at = el.getRootNode().host; at && at !== document.body; at = at.parentElement || at.getRootNode().host) {
		const style = getComputedStyle(at);
		if (/[0-9]/.test(style.zIndex) || +style.opacity < 1 || style.transform !== "none" || style.filter !== "none")
			at.classList.add("driver-fix-stacking");
	}
};
