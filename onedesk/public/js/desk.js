frappe.provide("onedesk");
// The rail rows below are set up while the dock is built, which can be before
// the rest of this file has run.
frappe.provide("onedesk.dock");

// A record being printed is still that record: frappe reads the print route as
// its own page, which only the Printing sidebar links, and so left the record's
// app for frappe's Print Format and Letter Head lists. It reads it as the
// record's doctype instead, so an invoice prints inside OneBook.
frappe.ui.Sidebar = class OneSidebar extends frappe.ui.Sidebar {
	// The workflow builder and the automation list and form are where Workspace ›
	// Approvals and Automations open, so they stay in One's sidebar rather than
	// frappe's Workflow and Automation ones: read as the page they open from.
	// They are workspace settings wherever they are opened from, a record's
	// Settings dialog in OneCRM included, so One's sidebar is taken even over
	// the one on screen or in the address, which frappe would otherwise keep.
	// Going back puts the address, and with it OneCRM's sidebar, back.
	shell_for_route(route) {
		if (OneSidebar.workspace(route) && frappe.boot.module_sidebars?.One) return "One";
		return super.shell_for_route(route);
	}

	add_standard_items(items) {
		const first = !this.standard_items_setup;
		super.add_standard_items(items);
		if (first) onedesk.dock.rows(this);
	}

	refresh_dock() {
		super.refresh_dock();
		if (this.dock) onedesk.dock.rail(this.dock);
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
		frappe.boot.canonical_shell = payload.canonical_shell;
		frappe.boot.home_shell = payload.home_shell;
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

// Frappe's, erpnext's and hrms's own workspaces are out of the boot (one/outside.py),
// so their addresses, and frappe's apps screen after signing in, go to One's Home.
if (frappe.boot.one_elsewhere) {
	for (const slug of frappe.boot.one_elsewhere) frappe.re_route[slug] = "one";
	frappe.re_route[""] = "one";
}

// What a person checks on: Search, Check In, OneIntake and Notifications. They
// sit at the foot of the rail, above the avatar, because the rail is on every
// page and the panel is not: a page with a sidebar of its own, such as My
// Tasks, OneMail or OneCloud, hides frappe's panel and the band under its
// header with it. frappe kept Search and the bell in the rail until its "make
// module sidebar primary"; these are its buttons, with its classes, so its
// search, its bell's count and its Notifications panel work from here
// (`rail`). On a phone there is no rail, and the band keeps them; with the rail
// pinned the band is hidden (desk.css), so nothing shows twice.
//
// Clocking in is one row rather than a route because it happens twice a day
// for everybody. The dot shows the state rather than offering a verb: green
// while clocked in, grey while not, and the click sends no direction because
// the server reads that from where the person already is.
onedesk.dock.rows = (sidebar) => {
	const $band = sidebar.$standard_items_band;
	const add = (item) => sidebar.add_item($band, { standard: true, type: "Button", ...item });
	add({
		label: __("Check In"),
		icon: "clock",
		class: "one-clock hide",
		suffix: `<span class="one-clock-dot"></span>`,
		onClick: () => onedesk.dock.punch(),
	});
	add({
		label: __("OneIntake"),
		icon: "inbox",
		class: "one-intake-row",
		suffix: `<span class="one-intake-count es-badge hide" data-variant="ghost"></span>`,
		onClick: () => frappe.set_route("intake"),
	});
	// Without the rail, the timers open from here: beside the row, or as a
	// page on a phone.
	if (onedesk.dock.times()) {
		add({
			label: __("Timers"),
			icon: "timer",
			class: "one-timers-row",
			suffix: `<span class="one-timers-count es-badge hide" data-variant="ghost"></span>`,
			onClick: () => onedesk.dock.timers_open($(".one-timers-row:visible").not(".one-rail-tool")[0]),
		});
	}
	onedesk.dock.refresh();
	// Intake: what OneAI did with what arrived, and what waits for you. A
	// number when something waits, a dot when something is unread.
	onedesk.dock.intake();
	// frappe's realtime drops a handler added before its socket exists.
	const listen = () => {
		frappe.realtime.on("intake_inbox", () => onedesk.dock.intake());
		frappe.realtime.on("one_timers", () => onedesk.dock.timers());
	};
	frappe.realtime.socket ? listen() : $(document).one("app_ready", listen);
};

// The rail's own tiles, at its foot above the avatar, each frappe's button for
// the same thing. Made once per rail.
onedesk.dock.rail = (dock) => {
	if (frappe.session.user === "Guest" || dock.$dock.find(".one-rail-tools").length) return;
	const $tools = $(`<div class="one-rail-tools"></div>`).insertBefore(dock.$dock.find(".dock-user"));
	const add = ({ label, icon, css, badge = "", click }) => {
		const $tile = $(
			`<button class="dock-item one-rail-tool ${css}" aria-label="${frappe.utils.escape_html(label)}">${frappe.utils.icon(icon, "md")}${badge}</button>`
		).appendTo($tools);
		if (click) $tile.on("click", click);
		$tile.data("one-tip", new frappe.ui.Tooltip($tile[0], { text: label, side: "right", delay: 0, offset: 10, class: "es-tooltip--plain" }));
		return $tile;
	};
	// page.js opens frappe's search from this class, wherever it is clicked.
	if (frappe.boot.desk_settings.search_bar) add({ label: __("Search"), icon: "search", css: "navbar-modal-search-mobile" });
	add({
		label: __("Check In"),
		icon: "clock",
		css: "one-clock hide",
		badge: `<span class="one-clock-dot"></span>`,
		click: () => onedesk.dock.punch(),
	});
	add({
		label: __("OneIntake"),
		icon: "inbox",
		css: "one-intake-row",
		badge: `<span class="one-intake-count one-rail-badge hide"></span>`,
		click: () => frappe.set_route("intake"),
	});
	if (onedesk.dock.times()) {
		add({
			label: __("Timers"),
			icon: "timer",
			css: "one-timers-row",
			badge: `<span class="one-timers-count one-rail-badge hide"></span>`,
			click: (event) => onedesk.dock.timers_open(event.currentTarget),
		});
	}
	if (frappe.boot.desk_settings.notifications) {
		// frappe's Notifications counts every `.notification-count`, and its panel
		// takes every `.sidebar-notification` as its button.
		const $bell = add({
			label: __("Notifications"),
			icon: "bell",
			css: "sidebar-notification",
			badge: `<span class="notification-count one-rail-badge hidden" aria-live="polite"></span>`,
			click: () => frappe.ui.sidebar_panels.toggle("notifications"),
		});
		const unread = frappe.boot.notification_unread_count || 0;
		$bell.find(".notification-count").text(unread > 99 ? "99+" : unread || "").toggleClass("hidden", !unread);
	}
	// Shown and hidden by frappe's BackgroundTasks, from its class.
	add({
		label: __("Background Tasks"),
		icon: "server",
		css: "sidebar-background-tasks hidden",
		click: () => frappe.ui.sidebar_panels.toggle("background-tasks"),
	}).toggleClass("hidden", !frappe.app.sidebar?.background_tasks?.db_tasks?.length);
	onedesk.dock.refresh();
	onedesk.dock.intake();
	onedesk.dock.timers();
};

// Whoever may keep a timesheet may time a task (one_task/timer.py).
onedesk.dock.times = () => frappe.session.user !== "Guest" && frappe.model.can_create("Timesheet");

// The reader's timers: how many, green while one runs. See one_task/timer.py.
onedesk.dock.timers = () => {
	if (!onedesk.dock.times()) return Promise.resolve(null);
	return frappe.xcall("onedesk.one_task.timer.timers").then((said) => {
		const $rows = $(".one-timers-row");
		const many = (said.running ? 1 : 0) + said.paused.length;
		$rows.find(".one-timers-count").toggleClass("hide", !many).toggleClass("one-timers-on", !!said.running).text(many || "");
		onedesk.dock.name(
			$rows,
			said.running ? __("Timing {0}", [said.running.subject]) : many ? __("{0} paused timers", [many]) : __("Timers")
		);
		return said;
	});
};

// The Timers popover: frappe-ui's Popover beside the tile or row clicked, with
// the onedesk.timers island in it, mounted the first time. The island tells
// it closed (onClose) when the reader clicks away or opens a task. A phone,
// with no room beside the band, opens the page instead.
onedesk.dock.timers_open = (el) => {
	if (!el || window.matchMedia("(max-width: 767px)").matches) return frappe.set_route("timers");
	const pop = (onedesk.dock._timers ||= { open: false });
	pop.open = !(pop.open && pop.reference === el);
	pop.reference = el;
	const props = { reference: el, open: pop.open };
	if (pop.island) return pop.island.update(props);
	const close = () => {
		pop.open = false;
		pop.island.update({ open: false });
	};
	const $host = $(`<div class="one-timers-host"></div>`).appendTo(document.body);
	pop.island = frappe.ui.mount_island("onedesk.timers", $host[0], { ...props, onClose: close });
};

// A row's or a tile's name, as read aloud and as the rail's tooltip says it.
onedesk.dock.name = ($item, label) =>
	$item.attr("aria-label", label).each((_, el) => $(el).data("one-tip")?.set_text(label));

// How many documents wait for the reader in Intake, and whether anything is
// unread. See one_intake/inbox.py.
onedesk.dock.intake = () =>
	frappe.xcall("onedesk.one_intake.inbox.counts").then((said) => {
		const $rows = $(".one-intake-row");
		const $badge = $rows.find(".one-intake-count");
		$badge.toggleClass("hide", !said.waiting && !said.unread);
		$badge.toggleClass("one-intake-dot", !said.waiting && !!said.unread);
		$badge.text(said.waiting ? (said.waiting > 99 ? "99+" : String(said.waiting)) : "");
		onedesk.dock.name($rows, said.waiting ? __("{0} waiting in OneIntake", [said.waiting]) : __("OneIntake"));
		return said;
	});


onedesk.dock.refresh = () =>
	onedesk.clock.ready().then((ready) => {
		const $item = $(".one-clock");
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
		onedesk.dock.name($item, label);
		$item.find(".sidebar-item-label").text(on ? __("Checked In") : __("Check In"));
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

// A plan's storage, in the 1000s it is sold in.
onedesk.tenant.size = (bytes) => onedesk.size(bytes, 1000) || __("nothing");

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
