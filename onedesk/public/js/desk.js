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
			label: __("OneIntake"),
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
	onedesk.dock.bar();
	onedesk.dock.refresh();
	onedesk.dock.intake();
	onedesk.dock.timers();
	const listen = () => {
		frappe.realtime.on("intake_inbox", () => onedesk.dock.intake());
		frappe.realtime.on("one_timers", () => onedesk.dock.timers());
	};
	frappe.realtime.socket ? listen() : $(document).one("app_ready", listen);
};

onedesk.dock.bar = () => {
	if (frappe.session.user === "Guest" || $(".one-bar").length) return;
	const $bar = $(`<header class="one-bar" role="toolbar" aria-label="${__("Tools")}">
		<div class="one-bar-lead">
			<div class="one-bar-group" data-group="dock"></div>
			<button class="one-bar-tool one-bar-now"></button>
			<div class="one-bar-group" data-group="open"></div>
		</div>
		<div class="one-bar-news hide" role="marquee" aria-label="${__("Announcements")}"></div>
		<div class="one-bar-tools">
			<div class="one-bar-group" data-group="find"></div>
			<div class="one-bar-group" data-group="day"></div>
			<div class="one-bar-group" data-group="waiting"></div>
			<div class="one-bar-group" data-group="ai"></div>
		</div>
	</header>`).prependTo(document.body);
	$("body").addClass("one-barred");
	onedesk.dock.place(frappe.defaults.get_user_default("one_bar") === "bottom" ? "bottom" : "top");
	const tip = (el, text) => new frappe.ui.Tooltip(el, { text, side: onedesk.dock.at === "bottom" ? "top" : "bottom", delay: 0, offset: 6, class: "es-tooltip--plain" });
	const add = ({ label, icon, css, badge = "", text = "", click, tip: said = label, group }) => {
		const $tile = $(
			`<button class="one-bar-tool ${css}" aria-label="${frappe.utils.escape_html(label)}"><span class="one-bar-icon">${frappe.utils.icon(
				icon,
				"sm"
			)}${badge}</span>${text}</button>`
		).appendTo($bar.find(`[data-group="${group}"]`));
		if (click) $tile.on("click", click);
		$tile.data("one-tip", tip($tile[0], said));
		return $tile;
	};
	if (frappe.boot.desk_settings.search_bar) {
		add({
			label: __("Search"),
			tip: `${__("Search")} ${frappe.utils.is_mac() ? "⌘K" : "Ctrl+K"}`,
			icon: "search",
			css: "navbar-modal-search-mobile",
			group: "find",
		});
	}
	add({
		label: __("Check In"),
		icon: "clock",
		css: "one-clock hide",
		badge: `<span class="one-clock-dot"></span>`,
		text: `<span class="one-clock-due hide"></span>`,
		click: () => onedesk.dock.punch(),
		group: "day",
	});
	if (onedesk.dock.times()) {
		add({
			label: __("Timers"),
			icon: "timer",
			css: "one-timers-row",
			badge: `<span class="one-timers-count one-bar-badge hide"></span>`,
			click: (event) => onedesk.dock.timers_open(event.currentTarget),
			group: "day",
		});
	}
	if (onedesk.apps.intake()) {
		add({
			label: __("OneIntake"),
			icon: "inbox",
			css: "one-intake-row",
			badge: `<span class="one-intake-count one-bar-badge hide"></span>`,
			click: () => frappe.set_route("intake"),
			group: "waiting",
		});
	}
	if (frappe.boot.desk_settings.notifications) {
		const $bell = add({
			label: __("Notifications"),
			icon: "bell",
			css: "sidebar-notification",
			badge: `<span class="notification-count one-bar-badge hidden" aria-live="polite"></span>`,
			click: () => frappe.ui.sidebar_panels.toggle("notifications"),
			group: "waiting",
		});
		const unread = frappe.boot.notification_unread_count || 0;
		$bell.find(".notification-count").text(unread > 99 ? "99+" : unread || "").toggleClass("hidden", !unread);
	}
	add({
		label: __("Background Tasks"),
		icon: "server",
		css: "sidebar-background-tasks hidden",
		click: () => frappe.ui.sidebar_panels.toggle("background-tasks"),
		group: "waiting",
	}).toggleClass("hidden", !frappe.app.sidebar?.background_tasks?.db_tasks?.length);
	if (onedesk.apps.ai()) {
		add({
			label: __("Ask {0}", ["OneAI"]),
			icon: "oneai",
			css: "one-ai-row",
			badge: `<span class="one-bar-badge hide"></span>`,
			click: () => onedesk.oneai.open(),
			group: "ai",
		});
	}
	onedesk.workbooks.place(add);
	const moved = () => (onedesk.dock.at === "bottom" ? __("Move This Bar to the Top") : __("Move This Bar to the Bottom"));
	const $move = add({
		label: moved(),
		icon: onedesk.dock.at === "bottom" ? "panel-top" : "panel-bottom",
		css: "one-bar-move",
		group: "dock",
		click: async () => {
			const at = onedesk.dock.at === "bottom" ? "top" : "bottom";
			onedesk.dock.place(at);
			$move.find("use").attr("href", `#icon-${at === "bottom" ? "panel-top" : "panel-bottom"}`);
			onedesk.dock.name($move, moved());
			$bar.find(".one-bar-tool").each((_, el) => $(el).data("one-tip")?.destroy?.());
			$bar.find(".one-bar-tool").each((_, el) => $(el).data("one-tip", tip(el, $(el).attr("aria-label"))));
			await frappe.xcall("onedesk.one.settings.place_bar", { at });
		},
	});
	const $now = $bar.find(".one-bar-now");
	if (!(frappe.boot.one_hidden?.apps || []).includes("OneCalendar")) $now.on("click", () => frappe.set_route("onecalendar"));
	onedesk.dock.now($now);
	$now.data("one-tip", tip($now[0], $now.attr("aria-label")));
	onedesk.dock.news(frappe.boot.one_announcements || []);
	clearInterval(onedesk.dock._ticking);
	onedesk.dock._ticking = setInterval(() => onedesk.dock.now($now), 15 * 1000);
};

/** Announcements run along the bar until they expire; one click opens one,
 * and Hide puts away those on it now, for this person; a new one still runs. */
onedesk.dock.news = (all) => {
	const esc = frappe.utils.escape_html;
	const $news = $(".one-bar-news");
	onedesk.dock._news = all;
	$news.toggleClass("hide", !all.length).empty();
	if (!all.length) return;
	const items = all
		.map(
			(one) =>
				`<button class="one-bar-news-item" data-note="${esc(one.name)}"><span class="one-bar-news-title">${esc(one.title)}</span>${
					one.text ? `<span class="one-bar-news-text">${esc(one.text)}</span>` : ""
				}</button>`
		)
		.join("");
	$news.html(
		`<span class="one-bar-news-icon">${frappe.utils.icon("megaphone", "sm")}</span><div class="one-bar-news-window"><div class="one-bar-news-track"><div class="one-bar-news-run">${items}</div></div></div><button class="one-bar-tool one-bar-news-hide" aria-label="${esc(
			__("Hide")
		)}">${frappe.utils.icon("x", "xs")}</button>`
	);
	const $track = $news.find(".one-bar-news-track");
	const $run = $track.children().first();
	if ($run[0].scrollWidth > $news.find(".one-bar-news-window").width()) {
		$run.clone().attr("aria-hidden", "true").find("button").attr("tabindex", "-1").end().appendTo($track);
		$news.addClass("one-bar-news-moving");
		$track.css("animation-duration", `${Math.max(12, Math.round($run[0].scrollWidth / 40))}s`);
	}
	$news.find("[data-note]").on("click", (event) => onedesk.dock.announcement($(event.currentTarget).attr("data-note")));
	$news.find(".one-bar-news-hide").on("click", () => {
		$news.addClass("hide");
		frappe.xcall("onedesk.one.announcements.hide");
	});
	if (!onedesk.dock._listening_news) {
		onedesk.dock._listening_news = true;
		const listen = () =>
			frappe.realtime.on("one_announcements", () => frappe.xcall("onedesk.one.announcements.current").then((now) => onedesk.dock.news(now || [])));
		frappe.realtime.socket ? listen() : $(document).one("app_ready", listen);
	}
};

onedesk.dock.announcement = async (name) => {
	const esc = frappe.utils.escape_html;
	const note = await frappe.db.get_doc("Note", name);
	const one = (onedesk.dock._news || []).find((row) => row.name === name) || {};
	const dialog = new frappe.ui.Dialog({
		title: note.title,
		fields: [{ fieldname: "said", fieldtype: "HTML" }],
		primary_action_label: __("All Announcements"),
		primary_action: () => {
			dialog.hide();
			frappe.set_route("List", "Note");
		},
	});
	dialog.fields_dict.said.$wrapper.html(
		`<div class="one-shell-quiet">${esc(one.by || frappe.user.full_name(note.owner))} · ${frappe.datetime.comment_when(note.creation)}</div><div class="msgprint">${note.content || ""}</div>`
	);
	dialog.show();
};

onedesk.dock.place = (at) => {
	onedesk.dock.at = at;
	$("body").toggleClass("one-bar-bottom", at === "bottom");
};

onedesk.dock.now = ($now) => {
	const zone = frappe.boot.time_zone?.user || frappe.boot.time_zone?.system;
	const now = zone && moment.tz ? moment().tz(zone) : moment();
	const time = now.format((frappe.datetime.get_user_time_fmt() || "HH:mm").replace(/:ss/, ""));
	$now.html(`<span class="one-bar-date">${frappe.utils.escape_html(now.format("ddd D MMM"))}</span><span class="one-bar-time">${frappe.utils.escape_html(time)}</span>`);
	onedesk.dock.name($now, now.format("dddd D MMMM YYYY"));
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
	const ours = (section) => {
		const known = { profile: "profile", notifications: "notifications" };
		frappe.set_route("settings", { section: known[section] || "profile" });
	};
	Object.defineProperty(frappe.ui, "show_user_settings", { get: () => ours, set: () => {}, configurable: true });
})();

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
