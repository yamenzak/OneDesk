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
frappe.ui.Sidebar = class OneSidebar extends frappe.ui.Sidebar {
	panel_can_close() {
		return false;
	}
};

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
				label: __("Intake"),
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
		const label = said.waiting ? __("Intake: {0} wait for you", [said.waiting]) : __("Intake");
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
		frappe.show_alert({ message: __("There is nothing to check in: you are {0} today.", [ready.state]) });
		return;
	}

	const reason = await onedesk.clock.why(ready.direction);
	if (ready.direction === "OUT" && !reason) return;

	frappe.dom.freeze(ready.direction === "IN" ? __("Checking in…") : __("Checking out…"));
	try {
		const done = await onedesk.clock.punch(ready, reason);
		onedesk.dock.told(done, ready);
	} catch (e) {
		frappe.show_alert({ message: __("The check-in could not be recorded."), indicator: "red" });
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
