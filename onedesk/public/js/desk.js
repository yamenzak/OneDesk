frappe.provide("onedesk");
// The rail rows below are set up while the dock is built, which can be before
// the rest of this file has run.
frappe.provide("onedesk.dock");

// The rail is five marks and never needs to be words: every entry is a product,
// and the panel beside it is where the reading happens. Frappe keeps the choice
// in localStorage and offers a toggle; One takes the choice away and gives the
// width to the panel.
frappe.ui.Dock = class OneDock extends frappe.ui.Dock {
	constructor(...args) {
		super(...args);
		this.collapsed = true;
		this.apply_collapsed();
	}

	toggle_collapsed() {}
};

// The panel is a column, not a flyout. `panel_can_close` is the single hinge:
// frappe asks it both for where the panel starts and for whether it may close,
// and answers yes whenever there is a rail, on the reasoning that a rail is the
// way back to a panel you dismissed. One is a product people work inside all
// day rather than a desk they dip into, so the panel stays out and the rail is
// for moving between products.
//
// A record being printed is still that record: frappe reads the print route as
// its own page, which only the Printing sidebar links, and so left the record's
// app for frappe's Print Format and Letter Head lists. It reads it as the
// record's doctype instead, so an invoice prints inside OneBook.
frappe.ui.Sidebar = class OneSidebar extends frappe.ui.Sidebar {
	panel_can_close() {
		return false;
	}

	// The workflow builder and the automation list and form are where Workspace ›
	// Approvals and Automations open, so they stay in One's rail rather than
	// frappe's Workflow and Automation ones: read as the page they open from.
	// They are workspace settings wherever they are opened from, a record's
	// Settings dialog in OneCRM included, so One's sidebar is taken even over
	// the one on screen, which frappe would otherwise keep (its step 1). The
	// sidebar they were opened from is remembered, so going back to the
	// customer puts OneCRM's back rather than keeping One's.
	resolve_sidebar_for(route, sticky, on_screen) {
		if (OneSidebar.workspace(route) && frappe.boot.module_sidebars?.One) {
			if (sticky && sticky !== "One") this.one_left = sticky;
			return { sidebar: "One", reason: "a workspace setting", provisional: false };
		}
		const left = this.one_left;
		this.one_left = null;
		if (left && sticky === "One" && !this.get_modules_linking(this.entity_from_route(route)).includes("One"))
			return super.resolve_sidebar_for(route, left, on_screen);
		return super.resolve_sidebar_for(route, sticky, on_screen);
	}

	entity_from_route(route) {
		if (OneSidebar.workspace(route)) return "workspace-settings";
		return route[0] === "print" && route[1] ? route[1] : super.entity_from_route(route);
	}

	link_type_from_route(route) {
		if (OneSidebar.workspace(route)) return "Page";
		return route[0] === "print" && route[1] ? "DocType" : super.link_type_from_route(route);
	}

	// What One's sidebar keeps wherever it is opened from: the workflow builder,
	// automations, a workspace's dashboards, their charts and cards, and its
	// reports by mail (one/reports.py), the Recycle Bin (one/recycle.py), the
	// Audit Log (one/audit.py) and privacy requests (one/privacy.py).
	static KEPT = [
		"Automation Flow",
		"Dashboard",
		"Dashboard Chart",
		"Number Card",
		"Auto Email Report",
		"Deleted Document",
		"Version",
		"Activity Log",
		"Access Log",
		"Personal Data Deletion Request",
		"Personal Data Download Request",
	];

	static workspace(route) {
		return (
			["workflow-builder", "dashboard-view"].includes(route[0]) ||
			(["List", "Form"].includes(route[0]) && OneSidebar.KEPT.includes(route[1]))
		);
	}
};

// A report saved from a list goes in its app's sidebar (one/reports.py); the
// sidebar is fetched again and drawn in place, as frappe's own sidebar editor does.
// frappe's realtime drops a handler added before its socket exists, so this waits
// for the desk.
$(document).on("app_ready", () =>
	frappe.realtime.on("one_sidebars", async () => {
		const payload = await frappe.xcall("onedesk.one.reports.sidebars");
		frappe.boot.module_sidebars = payload.module_sidebars;
		frappe.boot.entity_module = payload.entity_module;
		const sidebar = frappe.app.sidebar;
		if (!sidebar) return;
		sidebar.all_sidebar_items = frappe.boot.module_sidebars;
		if (frappe.boot.module_sidebars[sidebar.current_module]) {
			sidebar.setup(sidebar.current_module);
			sidebar.refresh();
		}
	})
);

// Frappe's Automation workspace is a second home for the same flows, in
// frappe's sidebar: /desk/automation goes to the list Workspace › Automations
// opens instead.
frappe.re_route["automation"] = "automation-flow";

// Clocking in belongs in the rail rather than at the end of a route. It is the
// one HR act that happens twice a day for everybody, and making it a
// destination — rail, Time, Check-ins, New — puts four decisions in front of a
// thing that should be one.
//
// `get_shortcuts()` is frappe's own list, with a documented item shape, and One
// already extends Dock to keep the rail collapsed. The dot shows the state
// rather than offering a verb: green while clocked in, grey while not, and the
// click sends no direction because the server reads that from where the person
// already is.
frappe.ui.Dock = class OneClockDock extends frappe.ui.Dock {
	get_shortcuts() {
		return [
			...super.get_shortcuts(),
			{
				name: "clock",
				icon: "clock",
				label: __("Check In"),
				css_class: "one-clock hide",
				badge: `<span class="one-clock-dot"></span>`,
				on_click: () => onedesk.dock.punch(),
				setup: ($item) => {
					onedesk.dock.$clock = $item;
					onedesk.dock.refresh();
				},
			},
			// Intake: what OneAI did with what arrived, and what waits for you.
			// A number when something waits, a dot when something is unread.
			{
				name: "intake",
				icon: "inbox",
				label: __("OneIntake"),
				css_class: "one-intake-rail",
				badge: `<span class="one-intake-count hide"></span>`,
				on_click: () => frappe.set_route("intake"),
				setup: ($item) => {
					onedesk.dock.$intake = $item;
					onedesk.dock.intake();
					frappe.realtime.on("intake_inbox", () => onedesk.dock.intake());
				},
			},
		];
	}
};

// How many documents wait for the reader in Intake, and whether anything is
// unread. See one_intake/inbox.py.
onedesk.dock.intake = () =>
	frappe.xcall("onedesk.one_intake.inbox.counts").then((said) => {
		const $badge = onedesk.dock.$intake && onedesk.dock.$intake.find(".one-intake-count");
		if (!$badge) return said;
		$badge.toggleClass("hide", !said.waiting && !said.unread);
		$badge.toggleClass("one-intake-dot", !said.waiting && !!said.unread);
		$badge.text(said.waiting ? (said.waiting > 99 ? "99+" : String(said.waiting)) : "");
		const label = said.waiting ? __("{0} waiting in OneIntake", [said.waiting]) : __("OneIntake");
		onedesk.dock.$intake.attr({ "aria-label": label, title: label });
		return said;
	});


onedesk.dock.refresh = () =>
	onedesk.clock.ready().then((ready) => {
		const $item = onedesk.dock.$clock;
		if (!$item) return ready;
		onedesk.dock.ready = ready;

		// No employee, or a workspace that has not switched clocking in on. The
		// row is built before either is known, so it hides itself afterwards
		// rather than being conditional on an answer nobody had yet.
		$item.toggleClass("hide", !ready.direction && !ready.state);

		const on = ready.state === "in" || ready.state === "late";
		$item.find(".one-clock-dot").toggleClass("one-clock-on", on);
		const label = on
			? __("Checked in {0}", [onedesk.clock.when(ready.since)])
			: ready.direction
				? __("Check In")
				: __("Not checking in today");
		$item.attr("aria-label", label);
		$item.attr("title", label);
		$item.find(".dock-item-label").text(on ? __("Checked In") : __("Check In"));
		return ready;
	});

onedesk.dock.punch = async () => {
	const ready = onedesk.dock.ready || (await onedesk.dock.refresh());
	if (!ready.direction) {
		frappe.show_alert({ message: __("Nothing to check in. You're {0} today.", [ready.state]) });
		return;
	}

	const reason = await onedesk.clock.why(ready.direction);
	if (ready.direction === "OUT" && !reason) return;

	frappe.dom.freeze(ready.direction === "IN" ? __("Checking in…") : __("Checking out…"));
	try {
		const done = await onedesk.clock.punch(ready, reason);
		onedesk.dock.told(done, ready);
	} catch (e) {
		frappe.show_alert({ message: __("Couldn't record the check-in."), indicator: "red" });
	} finally {
		frappe.dom.unfreeze();
		onedesk.dock.refresh();
	}
};

// A refusal says what was wrong in sentences rather than in a code, because a
// refusal nobody can act on is a phone call to HR.
onedesk.dock.told = (done, ready) => {
	if (done.register) {
		frappe.confirm(__("Register a passkey on this phone first?"), () =>
			onedesk.passkey.register().then(() => onedesk.dock.refresh())
		);
		return;
	}
	if (!done.ok) {
		// `clear` because msgprint appends to whatever dialog is already open, and
		// what is already open may be somebody else's message about something
		// else — HRMS's own Employee form asks `get_assignable_masters` on load
		// and an employee reading their own record gets a permission error back
		// from it. A refused clock-in says what was wrong with the clock-in.
		frappe.msgprint({
			title: __("Not Checked In"),
			indicator: "red",
			clear: true,
			message: (done.told || []).map((one) => frappe.utils.escape_html(one)).join("<br>"),
		});
		return;
	}
	frappe.show_alert({
		message: ready.direction === "IN" ? __("Checked In") : __("Checked Out"),
		indicator: done.flagged ? "orange" : "green",
	});
};

// Settings in the avatar menu is One's page rather than frappe's dialog: one
// place for what a person and a workspace set (one/settings.py). The menu
// loads the dialog's bundle before calling this, and the bundle would put its
// own back, so ours is held in place.
(() => {
	const ours = (section) => {
		const known = { profile: "profile", notifications: "notifications" };
		frappe.set_route("settings", { section: known[section] || "profile" });
	};
	Object.defineProperty(frappe.ui, "show_user_settings", { get: () => ours, set: () => {}, configurable: true });
})();

frappe.provide("onedesk.tenant");

// Bytes, in the units somebody says out loud. Base ten rather than base two,
// because that is what a plan is sold in and what a customer will compare it
// against.
onedesk.tenant.size = (bytes) => {
	const n = Number(bytes || 0);
	if (!n) return __("nothing");
	const units = ["B", "KB", "MB", "GB", "TB"];
	let at = 0;
	let left = n;
	while (left >= 1000 && at < units.length - 1) {
		left /= 1000;
		at += 1;
	}
	return `${left >= 10 || at === 0 ? Math.round(left) : left.toFixed(1)} ${units[at]}`;
};

// Frappe's workflow builder draws every field of a step, and its controls show a
// hidden one all the same. An approval tells whoever it waits on through One's hub
// (one/approvals.py), so frappe's own mail settings are not offered; and to
// somebody frappe does not let customize, neither is what an approval the
// workspace writes may not do: tasks a step runs, a value worked out by code.
$(document).on("startup", () => {
	document.body.toggleAttribute("data-one-held", !frappe.model.can_create("Custom Field"));
});

// A space's home is frappe's Workspace page, whose blocks frappe leaves empty
// for somebody who may not see what they hold (a chart, a card, a number), and
// whose headings it keeps all the same: an administrator with no sales role saw
// OneCRM's "My Day" and "The Pipeline" over nothing. An empty block is marked,
// and so is a heading with nothing shown under it before the next, with the
// spacers between; desk.css hides them, except while the page is being edited.
onedesk.tidy_home = ($body) => {
	const blocks = [...$body.find("#editorjs .ce-block")];
	// A custom block that has nothing to say hides its own block (One Needs
	// You, when nothing does): that is not shown either.
	const shown = (block) => {
		const held = block.querySelector(".ce-block__content > *");
		if (!held || block.style.display === "none") return false;
		return held.children.length > 0 || held.textContent.trim() !== "";
	};
	const kind = (block) => {
		const held = block.querySelector(".ce-block__content > *");
		if (!held) return "empty";
		if (held.classList.contains("ce-header")) return "heading";
		if (held.classList.contains("spacer")) return "spacer";
		if (block.style.display === "none") return "gone";
		return shown(block) ? "shown" : "empty";
	};
	let run = [];
	const close = () => {
		if (run.length && !run.some((block) => kind(block) === "shown")) run.forEach((block) => block.classList.add("one-block-empty"));
		run = [];
	};
	for (const block of blocks) {
		block.classList.remove("one-block-empty");
		const is = kind(block);
		if (is === "heading") close();
		if (is === "empty") block.classList.add("one-block-empty");
		if (is === "heading" || run.length) run.push(block);
	}
	close();
	// Nothing at all shown: frappe's empty state says so, rather than a blank
	// page, and goes as soon as a block draws.
	$body.find(".one-home-empty").remove();
	if (blocks.length && !blocks.some((block) => kind(block) === "shown")) {
		$(
			`<div class="one-home-empty">${onedesk.shell.empty(
				__("Nothing here yet"),
				__("Ask an administrator for access."),
				{ icon: "layout-grid" }
			)}</div>`
		).insertBefore($body.find("#editorjs"));
	}
};

$(document).on("app_ready", () => {
	const Workspace = frappe.views && frappe.views.Workspace;
	if (!Workspace || Workspace.prototype.one_tidied) return;
	Workspace.prototype.one_tidied = true;
	const shown = Workspace.prototype.show_page;
	Workspace.prototype.show_page = async function (page) {
		const out = await shown.call(this, page);
		// Blocks draw, and hide themselves, after the page does: tidied again
		// as they change, for the first few seconds.
		const body = this.body;
		onedesk.tidy_home(body);
		const again = frappe.utils.debounce(() => onedesk.tidy_home(body), 150);
		const watching = new MutationObserver((changes) => {
			if (changes.some((one) => !(one.attributeName === "class" && one.target.classList.contains("ce-block")))) again();
		});
		watching.observe(body[0], { childList: true, subtree: true, attributes: true, attributeFilter: ["style", "class"] });
		setTimeout(() => watching.disconnect(), 5000);
		return out;
	};
});
