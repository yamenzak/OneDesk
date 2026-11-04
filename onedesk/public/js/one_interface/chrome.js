// The frame around every screen (onedesk/one_interface/AGENTS.md): frappe's rail down the left,
// a bar across the top and a bar across the bottom, in the frame's colour,
// with the screen inset between them. The top bar is the workspace and what
// reaches you (its name, announcements, search, OneAI, notifications);
// the bottom bar is this window and what is running, as a taskbar is (the
// window's count and paging, open files, Check In and timers, OneAI, and the
// date and time at its end). The look is
// window/chrome.css; the colour is the workspace's (One's ControlCenter ›
// Branding › Frame Colour), and frame() applies it.
$.extend(onedesk.interface, {
	// The workspace's frame colour, as the frame's own token, and the ink that
	// reads on it, which the server works out by the letter heads' rule
	// (company.frame_ink): dark on a light colour, light on a dark one.
	frame(colour = frappe.boot.one_frame_colour, ink = frappe.boot.one_frame_ink) {
		const root = document.documentElement;
		if (!/^#[0-9a-f]{6}$/i.test(colour || "")) {
			root.style.removeProperty("--one-frame-brand");
			delete root.dataset.oneFrame;
			delete root.dataset.oneFrameInk;
			return;
		}
		root.style.setProperty("--one-frame-brand", colour);
		root.dataset.oneFrame = "brand";
		root.dataset.oneFrameInk = ink === "dark" ? "dark" : "light";
	},

	bars() {
		if (frappe.session.user === "Guest" || $(".one-bar").length) return;
		const $top = $(`<header class="one-bar" data-at="top" role="toolbar" aria-label="${__("Tools")}">
			<div class="one-bar-lead"><span class="one-bar-name"></span></div>
			<div class="one-bar-news hide" role="marquee" aria-label="${__("Announcements")}"></div>
			<div class="one-bar-tools">
				<div class="one-bar-group" data-group="find"></div>
				<div class="one-bar-group" data-group="waiting"></div>
			</div>
		</header>`).prependTo(document.body);
		const $bottom = $(`<footer class="one-bar" data-at="bottom" role="toolbar" aria-label="${__("Running")}">
			<div class="one-bar-lead">
				<div class="one-bar-status"></div>
				<div class="one-bar-group" data-group="open"></div>
			</div>
			<div class="one-bar-tools">
				<div class="one-bar-group" data-group="day"></div>
				<div class="one-bar-group" data-group="ai"></div>
				<div class="one-bar-group" data-group="weather"><button class="one-bar-tool one-bar-weather hide"></button></div>
				<div class="one-bar-group" data-group="when"><button class="one-bar-tool one-bar-now"></button></div>
			</div>
		</footer>`).appendTo(document.body);
		$top.find(".one-bar-name").text(frappe.boot.one_workspace_name || frappe.boot.sysdefaults?.company || "");
		$("body").addClass("one-barred");
		const $bars = $top.add($bottom);
		const tip = (el) =>
			new frappe.ui.Tooltip(el, {
				text: $(el).data("one-said") || $(el).attr("aria-label"),
				side: $(el).closest(".one-bar").attr("data-at") === "bottom" ? "top" : "bottom",
				delay: 0,
				offset: 6,
				class: "es-tooltip--plain",
			});
		const add = ({ label, icon, css, badge = "", text = "", click, tip: said = label, group }) => {
			const $tile = $(
				`<button class="one-bar-tool ${css}" aria-label="${frappe.utils.escape_html(label)}" data-one-label="${frappe.utils.escape_html(label)}"><span class="one-bar-icon">${frappe.utils.icon(
					icon,
					"sm"
				)}${badge}</span>${text}</button>`
			).appendTo($bars.find(`[data-group="${group}"]`));
			if (click) $tile.on("click", click);
			$tile.data("one-said", said).data("one-tip", tip($tile[0]));
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
		if (onedesk.apps.intake()) {
			add({
				label: __("Documents"),
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
		const $now = $bottom.find(".one-bar-now");
		if (!(frappe.boot.one_hidden?.apps || []).includes("OneCalendar")) $now.on("click", () => frappe.set_route("onecalendar"));
		onedesk.interface.now($now);
		$now.data("one-tip", tip($now[0]));
		onedesk.interface.weather($bottom.find(".one-bar-weather"), tip);
		onedesk.interface.news(frappe.boot.one_announcements);
		onedesk.interface.place_status();
		clearInterval(onedesk.interface._ticking);
		onedesk.interface._ticking = setInterval(() => onedesk.interface.now($now), 15 * 1000);
	},

	now($now) {
		const zone = frappe.boot.time_zone?.user || frappe.boot.time_zone?.system;
		const now = zone && moment.tz ? moment().tz(zone) : moment();
		const time = now.format((frappe.datetime.get_user_time_fmt() || "HH:mm").replace(/:ss/, ""));
		$now.html(
			`<span class="one-bar-date">${frappe.utils.escape_html(now.format("ddd D MMM"))}</span><span class="one-bar-time">${frappe.utils.escape_html(time)}</span>`
		);
		onedesk.dock.name($now, now.format("dddd D MMMM YYYY"));
	},

	/** The workspace's Default Place beside the clock (one/weather.py), asked
	 * for only when there is one and the Weather service is on, and again
	 * every quarter of an hour. One click opens the place. */
	weather($weather, tip) {
		const place = frappe.boot.one_weather;
		if (!place || !$weather.length) return;
		$weather.on("click", () => $weather.data("one-route") && frappe.set_route(...$weather.data("one-route")));
		const draw = () =>
			frappe.xcall("onedesk.one.weather.here").then((said) => {
				$weather.toggleClass("hide", !said?.temperature);
				if (!said?.temperature) return;
				$weather.data("one-route", said.route);
				const esc = frappe.utils.escape_html;
				$weather.html(
					`<span class="one-bar-icon">${frappe.utils.icon(said.icon, "sm")}</span><span class="one-bar-weather-temp">${esc(said.temperature)}</span>`
				);
				if (!$weather.data("one-tip")) $weather.data("one-tip", tip($weather[0]));
				const today = said.high ? __("{0}, high {1}, low {2}", [said.condition, said.high, said.low]) : said.condition;
				onedesk.dock.name($weather, `${said.place}: ${today}`);
			});
		draw();
		clearInterval(onedesk.interface._weathering);
		onedesk.interface._weathering = setInterval(draw, 15 * 60 * 1000);
	},

	/** Announcements run along the top bar until they expire, and one click
	 * opens one. ✕ folds them to the megaphone with how many there are, for
	 * this person; the megaphone opens them again, and so does a new one. */
	news(said) {
		const esc = frappe.utils.escape_html;
		const $news = $(".one-bar-news");
		said = said || {};
		onedesk.interface._said = said;
		const announced = said.running || [];
		const headlines = said.news || [];
		onedesk.interface._news = announced;
		if (!onedesk.interface._listening_news) {
			onedesk.interface._listening_news = true;
			const again = frappe.utils.debounce(
				() => frappe.xcall("onedesk.one.announcements.current").then((now) => onedesk.interface.news(now)),
				2000
			);
			const listen = () => {
				frappe.realtime.on("one_announcements", again);
				frappe.realtime.on("one_news", again);
			};
			frappe.realtime.socket ? listen() : $(document).one("app_ready", listen);
		}
		let shows = said.shows === "News" ? "News" : "Announcements";
		if (shows === "News" && !headlines.length) shows = "Announcements";
		if (shows === "Announcements" && !announced.length && headlines.length) shows = "News";
		const news = shows === "News";
		const rows = news ? headlines : announced;
		const other = news ? "Announcements" : "News";
		const both = announced.length && headlines.length;
		const redraw = (change) => onedesk.interface.news({ ...said, ...change });
		$news.toggleClass("hide", !rows.length).removeClass("one-bar-news-moving one-bar-news-folded").empty();
		if (!rows.length) return;
		const mark = news ? "newspaper" : "megaphone";
		if (news ? said.news_folded : said.folded) {
			$news.addClass("one-bar-news-folded").html(
				`<button class="one-bar-tool one-bar-news-open" aria-label="${esc(news ? __("News") : __("Announcements"))}"><span class="one-bar-icon">${frappe.utils.icon(
					mark,
					"sm"
				)}<span class="one-bar-badge">${rows.length}</span></span></button>`
			);
			$news.find(".one-bar-news-open").on("click", () => {
				frappe.xcall("onedesk.one.announcements.show", { what: shows });
				redraw(news ? { news_folded: false } : { folded: false });
			});
			return;
		}
		const items = rows
			.map((one, i) =>
				news
					? `<button class="one-bar-news-item" data-at="${i}">${
							one.logo ? `<img class="one-bar-news-logo" src="${esc(one.logo)}" alt="">` : ""
					  }<span class="one-bar-news-title">${esc(one.title)}</span>${
							one.publisher ? `<span class="one-bar-news-text">${esc(one.publisher)}</span>` : ""
					  }</button>`
					: `<button class="one-bar-news-item" data-note="${esc(one.name)}"><span class="one-bar-news-title">${esc(one.title)}</span>${
							one.text ? `<span class="one-bar-news-text">${esc(one.text)}</span>` : ""
					  }</button>`
			)
			.join("");
		const lead = both
			? `<button class="one-bar-tool one-bar-news-switch" aria-label="${esc(
					news ? __("Show Announcements") : __("Show News")
			  )}">${frappe.utils.icon(mark, "sm")}</button>`
			: `<span class="one-bar-news-icon">${frappe.utils.icon(mark, "sm")}</span>`;
		const choose = news
			? `<button class="one-bar-tool one-bar-news-choose" aria-label="${esc(__("Choose Sources"))}">${frappe.utils.icon("list-filter", "xs")}</button>`
			: "";
		$news.html(
			`${lead}<div class="one-bar-news-window"><div class="one-bar-news-track"><div class="one-bar-news-run">${items}</div></div></div>${choose}<button class="one-bar-tool one-bar-news-hide" aria-label="${esc(
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
		$news.find("[data-note]").on("click", (event) => onedesk.interface.announcement($(event.currentTarget).attr("data-note")));
		$news.find("[data-at]").on("click", (event) => {
			const one = headlines[Number($(event.currentTarget).attr("data-at"))] || {};
			if (one.link) window.open(one.link, "_blank", "noopener");
			else if (one.route && one.route.length) frappe.set_route(...one.route);
		});
		$news.find(".one-bar-news-switch").on("click", () => {
			frappe.xcall("onedesk.one.announcements.shows", { what: other });
			redraw({ shows: other });
		});
		$news.find(".one-bar-news-choose").on("click", () => onedesk.interface.choose_news());
		$news.find(".one-bar-news-hide").on("click", () => {
			frappe.xcall("onedesk.one.announcements.hide", { what: shows });
			redraw(news ? { news_folded: true } : { folded: true });
		});
	},

	/** Which News Sources run along this person's bar (one/news/desk.py):
	 * every one ticked is everything, and so is none. */
	async choose_news() {
		const said = await frappe.xcall("onedesk.one.news.desk.following");
		const dialog = new frappe.ui.Dialog({
			title: __("Choose Sources"),
			fields: [
				{
					fieldtype: "MultiCheck",
					fieldname: "sources",
					label: __("Sources"),
					columns: 2,
					options: said.sources.map((one) => ({
						label: one.name,
						value: one.name,
						checked: one.followed ? 1 : 0,
					})),
				},
			],
			primary_action_label: __("Save"),
			primary_action: async ({ sources }) => {
				dialog.hide();
				await frappe.xcall("onedesk.one.news.desk.follow", { sources });
				onedesk.interface.news(await frappe.xcall("onedesk.one.announcements.current"));
			},
		});
		dialog.show();
	},

	async announcement(name) {
		const esc = frappe.utils.escape_html;
		const note = await frappe.db.get_doc("Note", name);
		const one = (onedesk.interface._news || []).find((row) => row.name === name) || {};
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
		// Seen By, frappe's own, which its sign-in pop-up filled before
		// announcements moved to the bar.
		frappe.xcall("frappe.desk.doctype.note.note.mark_as_seen", { note: name }).catch(() => {});
	},
});

// A mark with a flat twin (scripts/icons.py) carries both on the rail, and
// chrome.css shows the twin on a workspace's own frame colour.
{
	const Dock = frappe.ui.Dock;
	if (Dock && !Dock.prototype.__one_flat) {
		Dock.prototype.__one_flat = true;
		const made = Dock.prototype.make_dock_item;
		const flat = () =>
			(Dock.flat ??= new Set(
				(frappe.boot.custom_icons || [])
					.filter(({ name }) => name.endsWith("-flat"))
					.map(({ name }) => name.slice(0, -5))
			));
		Dock.prototype.make_dock_item = function (entry) {
			const $item = made.call(this, entry);
			if ($item && flat().has(entry.icon)) {
				const twin = frappe.utils.icon(`${entry.icon}-flat`, "md", "", "", "one-flat");
				$item.find(".dock-item-icon").addClass("one-flat-icon").append(twin);
			}
			return $item;
		};
	}
}

onedesk.interface.frame();
$(document).on("app_ready", () => frappe.realtime.on("one_frame", (said) => onedesk.interface.frame(said.colour, said.ink)));
