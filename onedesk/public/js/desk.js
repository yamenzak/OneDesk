frappe.provide("onedesk");
frappe.provide("onedesk.dock");

// frappe.set_route("onecloud", { node }) names a page that is also an app's
// shell, and frappe asks whether the options after it name something before
// it sets them aside, which throws on an object. Every folder OneCloud opened
// that way went nowhere. Only a word can name something.
(() => {
	const router = frappe.router;
	if (!router || router.segment_kind.one_words) return;
	const kind = router.segment_kind;
	router.segment_kind = function (segment) {
		return typeof segment === "string" ? kind.call(this, segment) : null;
	};
	router.segment_kind.one_words = true;
})();

frappe.ui.Sidebar = class OneSidebar extends frappe.ui.Sidebar {
	shell_for_route(route) {
		if (this.kept(route) && frappe.boot.module_sidebars?.One) return "One";
		return super.shell_for_route(route);
	}

	add_standard_items(items) {
		const first = !this.standard_items_setup;
		super.add_standard_items(items);
		if (first) onedesk.dock.rows(this);
	}

	entity_from_route(route) {
		if (this.kept(route)) return "workspace-settings";
		return route[0] === "print" && route[1] ? route[1] : super.entity_from_route(route);
	}

	link_type_from_route(route) {
		if (this.kept(route)) return "Page";
		return route[0] === "print" && route[1] ? "DocType" : super.link_type_from_route(route);
	}

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

	// A dashboard or a tool's record a rail lists opens in that rail; one no
	// rail lists opens in One, under Workspace Settings.
	kept(route) {
		if (!OneSidebar.workspace(route)) return false;
		const entity = super.entity_from_route(route);
		return !entity || !this.get_modules_linking(entity, super.link_type_from_route(route)).length;
	}

	static workspace(route) {
		return (
			["workflow-builder", "dashboard-view"].includes(route[0]) ||
			(["List", "Form"].includes(route[0]) && OneSidebar.KEPT.includes(route[1]))
		);
	}
};

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

frappe.re_route["automation"] = "automation-flow";

if (frappe.boot.one_elsewhere) {
	for (const slug of frappe.boot.one_elsewhere) frappe.re_route[slug] = "one";
	frappe.re_route[""] = "one";
}

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
	if (onedesk.apps.intake()) {
		add({
			label: __("Documents"),
			icon: "inbox",
			class: "one-intake-row",
			suffix: `<span class="one-intake-count es-badge hide" data-variant="ghost"></span>`,
			onClick: () => frappe.set_route("intake"),
		});
	}
	if (onedesk.dock.times()) {
		add({
			label: __("Timers"),
			icon: "timer",
			class: "one-timers-row",
			suffix: `<span class="one-timers-count es-badge hide" data-variant="ghost"></span>`,
			onClick: () => onedesk.dock.timers_open($(".one-timers-row:visible").not(".one-bar-tool")[0]),
		});
	}
	onedesk.window.bars();
	onedesk.dock.refresh();
	onedesk.dock.intake();
	onedesk.dock.timers();
	const listen = () => {
		frappe.realtime.on("intake_inbox", () => onedesk.dock.intake());
		frappe.realtime.on("one_timers", () => onedesk.dock.timers());
	};
	frappe.realtime.socket ? listen() : $(document).one("app_ready", listen);
};

onedesk.dock.times = () => frappe.session.user !== "Guest" && frappe.model.can_create("Timesheet");

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

onedesk.dock.name = ($item, label) =>
	$item.attr("aria-label", label).each((_, el) => $(el).data("one-tip")?.set_text(label));

onedesk.dock.intake = () =>
	onedesk.apps.intake() &&
	frappe.xcall("onedesk.one_ai.reading.inbox.counts").then((said) => {
		const $rows = $(".one-intake-row");
		const $badge = $rows.find(".one-intake-count");
		$badge.toggleClass("hide", !said.waiting && !said.unread);
		$badge.toggleClass("one-intake-dot", !said.waiting && !!said.unread);
		$badge.text(said.waiting ? (said.waiting > 99 ? "99+" : String(said.waiting)) : "");
		onedesk.dock.name($rows, said.waiting ? __("{0} waiting in Documents", [said.waiting]) : __("Documents"));
		return said;
	});


onedesk.dock.refresh = () =>
	onedesk.clock.ready().then((ready) => {
		const $item = $(".one-clock");
		onedesk.dock.ready = ready;

		$item.toggleClass("hide", !ready.direction && !ready.state);

		const on = ready.state === "in";
		const due = !on && ready.direction === "IN" && ready.due ? onedesk.clock.time(ready.due) : "";
		$item.find(".one-clock-dot").toggleClass("one-clock-on", on && !ready.late).toggleClass("one-clock-late", !!ready.late);
		const word = on ? "" : ready.late ? __("Late") : due ? __("Check In") : "";
		$item.find(".one-clock-due").text(word).toggleClass("hide", !word);
		const label = on
			? ready.late
				? __("Checked in {0}, late", [onedesk.clock.when(ready.since)])
				: __("Checked in {0}", [onedesk.clock.when(ready.since)])
			: due
				? ready.late
					? __("Your shift started at {0}", [due])
					: __("Check in by {0}", [due])
				: ready.direction
					? __("Check In")
					: __("Not checking in today");
		onedesk.dock.name($item, label);
		$item
			.find(".sidebar-item-label")
			.text(on ? __("Checked In") : due ? (ready.late ? __("Late since {0}", [due]) : __("Check in by {0}", [due])) : __("Check In"));
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

onedesk.dock.told = (done, ready) => {
	if (done.register) {
		frappe.confirm(__("Register a passkey on this phone first?"), () =>
			onedesk.passkey.register().then(() => onedesk.dock.refresh())
		);
		return;
	}
	if (!done.ok) {
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

(() => {
	const ours = (section) =>
		section === "notifications" ? onedesk.notification_center.open() : onedesk.account_center.open({ at: "profile" });
	Object.defineProperty(frappe.ui, "show_user_settings", { get: () => ours, set: () => {}, configurable: true });
})();

// Every centre by its name (onedesk.CENTERS), and a centre opened from a
// link in a mail or a notification: /desk/one?center=account&at=plan opens
// AccountCenter on Plan and Credits over Home, and the address loses the
// question so that going back does not open it again.
frappe.provide("onedesk.centers");
onedesk.centers.open = (center, { at = null, record = null, module = null } = {}) => {
	const doors = {
		account: () => onedesk.account_center.open({ at, record }),
		// A module's ControlCenter (onedesk.control_centers), One's own when
		// no module is named, its files loaded first where they are not
		// loaded with the desk.
		settings: async () => {
			await frappe.require(onedesk.centers.FILES[module] || []);
			return (onedesk.control_centers[module || "One"] || onedesk.control_centers.One)({ at, record });
		},
		access: () => onedesk.access.open({ module, at, record }),
		notifications: () => onedesk.notification_center.open({ module, at }),
		ai: () => onedesk.ai_center.open({ module, at }),
		trust: () => onedesk.trust.open({ module, at }),
	};
	return (doors[center] || doors.account)();
};
onedesk.centers.FILES = {
	OneMail: ["/assets/onedesk/js/one_mail/onemail_settings.js", "/assets/onedesk/css/one_mail/onemail_settings.css"],
};
$(document).on("page-change", () => {
	onedesk.centers.here = null;
	const asked = frappe.utils.get_query_params();
	if (!asked.center) return;
	window.history.replaceState(null, "", window.location.pathname);
	onedesk.centers.open(asked.center, asked);
});

frappe.provide("onedesk.tenant");

onedesk.tenant.size = (bytes) => onedesk.size(bytes, 1000) || __("nothing");

$(document).on("startup", () => {
	document.body.toggleAttribute("data-one-held", !frappe.model.can_create("Custom Field"));
});

onedesk.tidy_home = ($body) => {
	const blocks = [...$body.find("#editorjs .ce-block")];
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
