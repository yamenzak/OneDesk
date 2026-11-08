// The look (onedesk/one_interface/AGENTS.md, Looks): how the frame and
// frappe's own screens in it are drawn. A look is a stylesheet scoped to
// `data-one-look` on the page and a set of parts the renderer turns on for
// it; the screens underneath are frappe's and the same in every look. Theme
// (light, dark) and palette (palettes.css) ride on top of any look.
frappe.provide("onedesk.interface");

onedesk.interface.LOOKS = {
	// frappe's desk on the frame, as it was before Canvas
	classic: {},
	// the record and the list on a quiet canvas, each one sheet on it
	canvas: {
		head: true, strip: true, thread: true, quiet: true, icons: true,
		offered: true,
		label: __("Canvas"),
		// the palettes drawn for it, the first one by default
		palettes: ["sand"],
	},
};

// The palettes a person may choose (palettes.css). Slate (id `standard`) is
// frappe-ui's own greys and every look has it; a look names the others it was
// drawn for, and the first of them is what a person sees until they choose.
onedesk.interface.PALETTES = {
	standard: { label: __("Slate") },
	sand: { label: __("Sand") },
};

// Each person's look, kept with their palette (Appearance, theme.js), else
// the workspace's. Only a look that is offered may be chosen.
onedesk.interface.looks = () => Object.keys(onedesk.interface.LOOKS).filter((name) => onedesk.interface.LOOKS[name].offered);
onedesk.interface.look = () => {
	const kept = onedesk.interface.kept("look", "");
	if (onedesk.interface.looks().includes(kept)) return kept;
	const asked = frappe.boot.one_look;
	return asked in onedesk.interface.LOOKS ? asked : "canvas";
};
onedesk.interface.uses = (part) => !!onedesk.interface.LOOKS[onedesk.interface.look()][part];
document.documentElement.dataset.oneLook = onedesk.interface.look();

// ── Palettes in islands ────────────────────────────────────────────────
// An island draws in a shadow root with frappe-ui's own greys, which no page
// variable reaches. Under a palette each island adopts this sheet, which
// points its greys at the same roles the desk's read (the steps no role
// stands for at the page's, handed down as --one-page-*), and its corners and
// font at the palette's, and its root carries the palette.
// Standard leaves islands exactly as frappe-ui draws them.
const ISLAND_PALETTE = new CSSStyleSheet();
ISLAND_PALETTE.replaceSync(`.frappe-island-root[data-one-palette], .frappe-island-portal[data-one-palette], .one-island-part-root[data-one-palette] { --surface-base: var(--one-surface); --surface-gray-1: var(--one-tint); --surface-gray-2: var(--one-hover); --surface-gray-3: var(--one-press); --surface-gray-4: var(--one-fill); --surface-gray-10: var(--one-primary-bg); --surface-elevation-1: var(--one-surface); --surface-elevation-2: var(--one-card-bg); --surface-elevation-3: var(--one-raised-bg); --ink-base: var(--one-primary-ink); --ink-gray-9: var(--one-ink-strong); --ink-gray-8: var(--one-ink); --ink-gray-7: var(--one-ink-soft); --ink-gray-6: var(--one-ink-quiet); --ink-gray-5: var(--one-ink-muted); --ink-gray-4: var(--one-ink-faint); --ink-gray-3: var(--one-placeholder); --outline-gray-1: var(--one-line); --outline-gray-2: var(--one-edge); --outline-gray-3: var(--one-edge-strong); --outline-gray-4: var(--one-edge-heavy); --surface-gray-5: var(--one-page-surface-gray-5); --surface-gray-6: var(--one-page-surface-gray-6); --surface-gray-7: var(--one-page-surface-gray-7); --surface-gray-8: var(--one-page-surface-gray-8); --surface-gray-9: var(--one-page-surface-gray-9); --ink-gray-1: var(--one-page-ink-gray-1); --ink-gray-2: var(--one-page-ink-gray-2); --outline-gray-5: var(--one-page-outline-gray-5); --outline-gray-6: var(--one-page-outline-gray-6); --outline-gray-7: var(--one-page-outline-gray-7); --outline-gray-8: var(--one-page-outline-gray-8); --outline-gray-9: var(--one-page-outline-gray-9); --radius-1: var(--one-radius-small); --radius-2: var(--one-radius-small); --radius-3: var(--one-radius-row); --radius-4: var(--one-radius-row); --radius-5: var(--one-radius-control); --radius-6: var(--one-radius-sheet); --radius-7: var(--one-radius-dialog); --radius-8: var(--one-radius-large); font-family: var(--one-font); }`);

// In Arabic, a line cut to fit keeps the start of a Latin name: it takes its
// direction from its own text, so the ellipsis falls at its end.
const ISLAND_RTL = new CSSStyleSheet();
ISLAND_RTL.replaceSync(`.truncate:dir(rtl) { unicode-bidi: plaintext; text-align: right; }`);

onedesk.interface.palette = () => document.documentElement.dataset.onePalette || "";
onedesk.interface.palettes = () => [...(onedesk.interface.LOOKS[onedesk.interface.look()].palettes || []), "standard"];

// Each person's palette is kept in their user settings with the rest of the
// window's (frame.js), and drawn before the first screen.
onedesk.interface.set_palette = (name, keep) => {
	const chosen = onedesk.interface.palettes().includes(name) ? name : "standard";
	if (chosen === "standard") delete document.documentElement.dataset.onePalette;
	else document.documentElement.dataset.onePalette = chosen;
	if (keep) onedesk.interface.keep("palette", chosen);
	return chosen;
};
onedesk.interface.set_palette(onedesk.interface.kept("palette", onedesk.interface.palettes()[0]));

const dress = (host) => {
	const shadow = host.shadowRoot;
	if (!shadow) return;
	const missing = [ISLAND_PALETTE, ISLAND_RTL].filter((one) => !shadow.adoptedStyleSheets.includes(one));
	if (missing.length) shadow.adoptedStyleSheets = [...shadow.adoptedStyleSheets, ...missing];
	const palette = onedesk.interface.palette();
	for (const root of shadow.children) {
		if (!root.hasAttribute("data-theme")) continue;
		if (host.classList.contains("one-island-part")) root.classList.add("one-island-part-root");
		if (palette) root.setAttribute("data-one-palette", palette);
		else root.removeAttribute("data-one-palette");
	}
};
const islands = () => document.querySelectorAll(".frappe-island, .one-island-part");
// frappe's mount sets an island's sheets once its stylesheets load, after the
// host is in the page, so a host is dressed again when its app first draws.
const watch = (host) => {
	if (host.__one_dressed || !host.shadowRoot) return;
	host.__one_dressed = true;
	dress(host);
	const drawn = new MutationObserver(() => {
		dress(host);
		drawn.disconnect();
	});
	drawn.observe(host.shadowRoot, { childList: true, subtree: true });
};
new MutationObserver((changes) => {
	for (const change of changes)
		for (const node of change.addedNodes)
			if (node.nodeType === 1) [node, ...node.querySelectorAll(".frappe-island, .one-island-part")].filter((one) => one.matches?.(".frappe-island, .one-island-part")).forEach(watch);
}).observe(document.documentElement, { childList: true, subtree: true });
new MutationObserver(() => islands().forEach(dress)).observe(document.documentElement, { attributes: true, attributeFilter: ["data-one-palette"] });
islands().forEach(watch);

const esc = (value) => frappe.utils.escape_html(String(value ?? ""));
const DATED = /(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4})/g;
const isolated = (value) => esc(value).replace(DATED, "<bdi>$1</bdi>");
const declared = (doctype) => (frappe.boot.one_interface || {})[doctype] || null;

onedesk.interface.label_icon = (label) => {
	const said = ` ${((label || "").toLowerCase().match(/[a-z0-9]+/g) || []).join(" ")} `;
	const found = (frappe.boot.one_icons?.phrases || []).find(([phrase]) => said.includes(` ${phrase} `));
	return found ? found[1] : null;
};

onedesk.interface.field_icon = (df) => {
	const shared = frappe.boot.one_icons;
	if (!shared || shared.none.includes(df.fieldtype)) return null;
	return onedesk.interface.label_icon(df.label) || shared.types[df.fieldtype] || null;
};
const icon = (name) => `<span class="one-ico">${frappe.utils.icon(name, "sm")}</span>`;

// ── A record ────────────────────────────────────────────────────────────

frappe.provide("onedesk.interface.record");
const record = onedesk.interface.record;

// The head above the tabs: the record's picture, its name and state, its ID
// when that is not the name, its track and the cards its module declares.
record.head = (frm) => {
	const container = frm.page && frm.page.wrapper && frm.page.wrapper[0];
	const pageHead = container && container.querySelector(":scope > .page-head, .page-head");
	if (!pageHead) return;
	// a new record has a head too: its name says New, its commands sit by it
	const shown = true;
	const fresh = frm.is_new();
	container.classList.toggle("one-has-head", shown);
	let hero = container.one_hero;
	if (!hero) {
		hero = document.createElement("div");
		hero.className = "one-hero one-hero-record";
		hero.innerHTML = `<div class="one-hero-row"><div class="one-hero-face" hidden></div><div class="one-hero-main"><div class="one-hero-title"><h1></h1></div></div></div><div class="one-head-cards"></div>`;
		container.one_hero = hero;
	}
	if (hero.previousElementSibling !== pageHead) pageHead.after(hero);
	hero.dataset.tour = `record-${frappe.scrub(frm.doctype).replace(/_/g, "-")}`;
	hero.querySelector(".one-head-cards").dataset.tour = "record-cards";
	hero.hidden = !shown;
	if (!shown) return;

	// the tabs sit under the head
	const row = pageHead.querySelector(".one-interface-row");
	if (row) {
		row.classList.add("one-tabs-below");
		if (hero.nextElementSibling !== row) hero.after(row);
	}

	const title = hero.querySelector(".one-hero-title");
	const name = fresh ? __("New {0}", [__(frm.doctype)]) : frm.doc[frm.meta.title_field] || frm.doc.name;
	title.querySelector("h1").textContent = name;
	const pill = pageHead.querySelector(".page-indicator-pill") || title.querySelector(".page-indicator-pill");
	if (pill && pill.parentElement !== title) title.append(pill);

	// what acts on the record stands by its name, as New stands by a list's,
	// and leaves the address row its room: frappe's primary and its
	// commands, and the buttons a doctype adds. Moved, so frappe's references
	// to them still work.
	let actions = hero.querySelector(".one-hero-actions");
	if (!actions) {
		actions = document.createElement("div");
		actions.className = "one-hero-actions";
		title.append(actions);
	}
	const commands = pageHead.querySelector(".one-interface-commands");
	const extra = pageHead.querySelector(".page-head-content > .standard-items-section");
	if (commands && commands.parentElement !== actions) actions.append(commands);
	if (extra && extra.parentElement !== actions) actions.append(extra);

	// frappe's own picture, moved, so its upload and remove still work
	const face = hero.querySelector(".one-hero-face");
	const section = container.querySelector(".form-sidebar .sidebar-image-section");
	const picture = section && section.querySelector(".sidebar-image-wrapper");
	if (frm.meta.image_field && picture) {
		face.replaceChildren(picture);
		section.classList.add("one-gone");
	}
	face.hidden = !(frm.meta.image_field && face.children.length);

	// the ID, a quiet line under the name, copied when clicked
	hero.querySelector(".one-hero-name")?.remove();
	if (!fresh && frm.doc.name && frm.doc.name !== name && frm.meta.autoname !== "hash") {
		const id = document.createElement("button");
		id.className = "one-hero-name";
		id.title = __("Copy");
		id.innerHTML = `<span>${esc(frm.doc.name)}</span>${frappe.utils.icon("copy", "xs")}`;
		id.onclick = () => frappe.utils.copy_to_clipboard(frm.doc.name);
		title.after(id);
	}

	const said = (frm.doc.__onload && frm.doc.__onload.one_head) || {};
	const rows = Object.fromEntries((said.band || []).map((one) => [one.key, one]));
	const charts = Object.fromEntries((said.charts || []).map((one) => [one.key, one]));
	const reg = declared(frm.doctype) || {};

	// the track: the steps of the row the module names, or the first that has steps
	hero.querySelector(".one-track")?.remove();
	const stepped = (reg.track && rows[reg.track]) || (said.band || []).find((one) => one.steps && one.steps.length);
	const steps = stepped && stepped.steps;
	if (steps && steps.length) {
		const track = document.createElement("div");
		track.className = "one-track";
		track.dataset.tour = "record-track";
		steps.forEach((step, i) => {
			const done = step.state === "done";
			const joined = done && steps[i + 1] && steps[i + 1].state === "done";
			track.insertAdjacentHTML(
				"beforeend",
				`<div class="one-track-step ${done ? "is-done" : "is-todo"}"><div class="one-track-mark"><span class="one-track-dot">${done ? frappe.utils.icon("check", "xs") : ""}</span>${i < steps.length - 1 ? `<span class="one-track-line ${joined ? "is-done" : ""}"></span>` : ""}</div><div class="one-track-text">${esc(step.label)}<small class="${step.state === "late" ? "is-late" : ""}">${isolated(step.note || "")}</small></div></div>`
			);
		});
		// at the head's far end, across from the name: where it stands, read at a glance
		hero.querySelector(".one-hero-row").append(track);
	}

	// the cards: the homes' figures, one per key the module names, in its order
	const TONE = { alarm: "red", waiting: "orange" };
	const change = (series) => {
		const [before, now] = (series || []).slice(-2);
		return before > 0 && now >= 0 ? Math.round(((now - before) / before) * 100) : null;
	};
	const cards = (reg.cards || [])
		.map((card) => {
			const named = card.title ? __(card.title) : null;
			const chart = charts[card.key];
			if (chart) {
				const total = chart.values.reduce((sum, one) => sum + one, 0);
				return { title: named || chart.label, value: format_currency(total, chart.currency, 0), series: chart.values, type: chart.kind === "line" ? "area" : "bar", delta: change(chart.values), deltaCaption: __("vs last month"), route: chart.route };
			}
			const one = rows[card.key];
			if (!one || one.value === "—") return null;
			const bar = one.meter && one.meter.of ? Math.min(100, Math.round((100 * one.meter.value) / one.meter.of)) : null;
			const at = one.when && (one.short ? $("<div>").html(frappe.datetime.comment_when(one.when, true)).text() : frappe.datetime.prettyDate(one.when));
			const filled = (text) => (at && text ? String(text).replace("{when}", at) : text);
			return { title: filled(named || one.label), value: filled(one.value), note: one.note || null, bar, tone: TONE[one.tone] || null, route: one.route };
		})
		.filter(Boolean);
	const host = hero.querySelector(".one-head-cards");
	host.hidden = !cards.length;
	if (cards.length) {
		if (container.one_cards) container.one_cards.update({ cards });
		else container.one_cards = frappe.ui.mount_island("onedesk.head", host, { cards });
	}

	// what the head now says, the panel's Overview no longer repeats
	const panel = frm.one_panel;
	const tabs = container.querySelectorAll(".one-panel .es-tabs__tab");
	const took = !!(steps && steps.length) || cards.length > 0;
	container.classList.toggle("one-head-took", took);
	if (panel && tabs.length > 1) {
		tabs[0].classList.toggle("one-gone", took);
		if (took && panel.tabs.active === 0) {
			panel.picking = true;
			panel.tabs.set_active(1);
			panel.picking = false;
		}
	}
	tabs.forEach((tab) => {
		const label = tab.getAttribute("title") || tab.getAttribute("aria-label");
		if (label && tab.textContent.trim() !== label) tab.textContent = label;
	});

	// the star ends the address row, as a browser's ends its address bar
	const drawn = [container, pageHead].flatMap((root) => [...root.querySelectorAll(".form-stats-likes .liked-by:not(.one-star)")])[0];
	if (drawn) {
		container.one_star?.remove();
		container.one_star = drawn;
	}
	const star = container.one_star;
	const place = pageHead.querySelector(".page-title");
	if (star && place) {
		container.one_star = star;
		star.classList.add("one-star");
		if (star.parentElement !== place) {
			place.append(star);
			frappe.ui.setup_like_popover($(place), ".like-icon");
		}
	}

	// print and OneCloud stay in the address row, before refresh and the
	// menu, when the record's commands go to stand by its name
	const tools = pageHead.querySelector(".one-interface-tools");
	const likes = container.querySelector(".form-sidebar .form-stats-likes");
	if (tools && likes) {
		container.querySelectorAll(".one-bar-icons").forEach((old) => old !== likes && old.remove());
		likes.classList.add("one-bar-icons");
		if (likes.parentElement !== tools) tools.prepend(likes);
	}
	// frappe's phone search came with its buttons to the name; it searches
	// everywhere, so it goes back to the address row
	const glass = hero.querySelector(".navbar-modal-search-mobile");
	if (tools && glass) tools.prepend(glass);
};

// What a saved record holds is shown; an empty field that isn't asked for
// waits behind one button, a field's help is a mark beside its label, a
// section with nothing shown goes, and so does a tab.
record.show_empty = (count) => (count === 1 ? __("Show 1 Empty Field") : __("Show {0} Empty Fields", [count]));

record.quiet_tabs = (frm) => {
	const page = frm.layout && frm.layout.wrapper && frm.layout.wrapper[0];
	const tabs = frm.layout && frm.layout.tabs;
	if (!page || !tabs || !tabs.length) return;
	const open = (page.querySelector(".form-page") || page).classList.contains("one-open");
	const shows = (tab) =>
		[...tab.wrapper[0].querySelectorAll(".form-section")].some(
			(section) => !section.classList.contains("empty-section") && !section.classList.contains("hide-control") && !section.classList.contains("one-quiet-section")
		);
	tabs.forEach((tab) => tab.tab_link && tab.tab_link[0].classList.toggle("one-quiet-tab", !open && !tab.hidden && !shows(tab)));
	const active = tabs.find((tab) => tab.is_active());
	if (active && active.tab_link[0].classList.contains("one-quiet-tab")) {
		const first = tabs.find((tab) => !tab.hidden && !tab.tab_link[0].classList.contains("one-quiet-tab"));
		first && first.set_active();
	}
};

record.fields = (frm) => {
	const page = frm.layout && frm.layout.wrapper && frm.layout.wrapper[0];
	if (!page) return;
	const saved = !frm.is_new();
	const LAYOUT = ["Section Break", "Column Break", "Tab Break", "HTML", "Button", "Heading", "Fold"];
	const NUMBER = ["Int", "Float", "Currency", "Percent"];
	const empty = (df) => {
		const value = frm.doc[df.fieldname];
		if (df.fieldtype === "Table" || df.fieldtype === "Table MultiSelect") return !(value && value.length);
		if (df.fieldtype === "Check") return !value;
		return value === null || value === undefined || value === "" || (value === 0 && !NUMBER.includes(df.fieldtype));
	};
	page.querySelectorAll(".form-section").forEach((el) => el.classList.toggle("one-headless", !el.querySelector(":scope > .section-head")));
	page.querySelectorAll(".one-quiet").forEach((el) => el.classList.remove("one-quiet"));
	page.querySelectorAll(".one-quiet-section").forEach((el) => el.classList.remove("one-quiet-section"));
	let quiet = 0;
	if (onedesk.interface.uses("quiet")) {
		page.querySelectorAll(".form-section").forEach((section) => {
			const controls = [...section.querySelectorAll(".frappe-control[data-fieldname]")].filter((el) => {
				const df = frm.fields_dict[el.dataset.fieldname] && frm.fields_dict[el.dataset.fieldname].df;
				return df && !LAYOUT.includes(df.fieldtype) && !el.classList.contains("hide-control");
			});
			let hidden = 0;
			controls.forEach((el) => {
				const df = frm.fields_dict[el.dataset.fieldname].df;
				if (saved && !df.reqd && empty(df)) {
					el.classList.add("one-quiet");
					hidden++;
				}
			});
			quiet += hidden;
			if (controls.length && controls.length === hidden) section.classList.add("one-quiet-section");
		});
	}
	let more = page.querySelector(":scope .one-more-all");
	if (quiet) {
		if (!more) {
			more = document.createElement("button");
			more.className = "one-more one-more-all";
			more.onclick = () => {
				const form = page.querySelector(".form-page") || page;
				form.classList.toggle("one-open");
				more.textContent = form.classList.contains("one-open") ? __("Hide Empty Fields") : record.show_empty(Number(more.dataset.count));
				record.quiet_tabs(frm);
			};
			(page.querySelector(".form-page") || page).append(more);
		}
		more.dataset.count = quiet;
		const open = (page.querySelector(".form-page") || page).classList.contains("one-open");
		more.textContent = open ? __("Hide Empty Fields") : record.show_empty(quiet);
	} else if (more) more.remove();
	record.quiet_tabs(frm);

	// a field's help is a mark beside its label
	page.querySelectorAll(".frappe-control").forEach((el) => {
		const help = el.querySelector(".help-box");
		const label = el.querySelector(".control-label, .label-area");
		const said = help && help.textContent.trim();
		if (!said || !label) return;
		let mark = label.querySelector(".one-help");
		if (!mark) {
			mark = document.createElement("span");
			mark.className = "one-help";
			mark.textContent = "i";
			label.append(mark);
		}
		mark.title = said;
		mark.onclick = (event) => {
			event.preventDefault();
			event.stopPropagation();
			help.classList.toggle("one-gone");
		};
		help.classList.add("one-gone");
	});

	// a box shows its whole value on hover when it is longer than the box
	page.querySelectorAll(".section-body input.form-control").forEach((input) => {
		input.title = input.scrollWidth > input.clientWidth + 1 ? input.value : "";
	});

	// a tab with nothing to show is dropped, and the first that has opens
	const tabs = (frm.layout && frm.layout.tabs) || [];
	if (tabs.length) {
		const shows = (control) =>
			!control.classList.contains("hide-control") && !control.classList.contains("one-quiet") && (control.dataset.fieldtype !== "HTML" || (control.innerText || "").trim());
		const bare = tabs.filter((tab) => ![...tab.wrapper[0].querySelectorAll(".frappe-control")].some(shows));
		tabs.forEach((tab) => tab.toggle(!bare.includes(tab)));
		const active = tabs.find((tab) => tab.is_active());
		if (!active || bare.includes(active)) {
			const first = tabs.find((tab) => !bare.includes(tab));
			if (first) first.set_active();
		}
	}
};

// A record's tabs and fields wear the shared registry's icons, or the one its
// module names where it means to differ.
record.icons = (frm) => {
	const reg = declared(frm.doctype) || {};
	((frm.layout && frm.layout.tabs) || []).forEach((tab) => {
		const link = tab.tab_link && (tab.tab_link[0] || tab.tab_link).querySelector && (tab.tab_link[0] || tab.tab_link).querySelector(".nav-link");
		const name = (reg.tabs && reg.tabs[tab.df.fieldname]) || onedesk.interface.label_icon(tab.df.label);
		if (name && link && !link.querySelector(".one-ico")) link.insertAdjacentHTML("afterbegin", icon(name).replace("one-ico", "one-ico one-tab-ico"));
	});
	Object.entries(frm.fields_dict || {}).forEach(([field, control]) => {
		const name = (reg.fields && reg.fields[field]) || (control?.df && onedesk.interface.field_icon(control.df));
		const label = name && control.$wrapper && control.$wrapper[0] && control.$wrapper[0].querySelector(".control-label");
		if (label && !label.querySelector(".one-ico")) label.insertAdjacentHTML("afterbegin", icon(name));
	});
};

// A record's shortcuts are rows of the panel: their own icon, a plain label
// and a mark at the end for what happens (+ makes a record, an arrow opens a
// list, a chevron anything else).
record.shortcuts = (frm) => {
	const box = frm.page.wrapper[0].querySelector(".form-sidebar .user-actions");
	if (!box) return;
	const TRAIL = { new: "plus", list: "arrow-up-right", open: "arrow-up-right" };
	box.querySelectorAll(".user-action-link").forEach((link) => {
		if (link.querySelector(".one-trail")) return;
		link.querySelector(".user-action-external-icon")?.remove();
		link.insertAdjacentHTML("beforeend", `<span class="one-trail">${frappe.utils.icon(TRAIL[link.dataset.kind] || "chevron-right", "sm")}</span>`);
	});
};

record.draw = (frm) => {
	if (!frm || !frm.page || !frm.page.interface) return;
	if (onedesk.interface.uses("head")) record.head(frm);
	record.fields(frm);
	if (onedesk.interface.uses("icons")) {
		record.icons(frm);
		setTimeout(() => record.icons(frm), 700);
	}
	if (onedesk.interface.uses("head")) record.shortcuts(frm);
};

// Drawn after frappe's refresh, and again once the form has settled (its
// sidebar, panel and links arrive a moment after).
$(document).on("form-refresh", (_e, frm) => {
	if (!onedesk.interface.uses("head") && !onedesk.interface.uses("quiet")) return;
	record.draw(frm);
	clearTimeout(frm.one_settle);
	frm.one_settle = setTimeout(() => record.draw(frm), 400);
});

// ── A record's activity ─────────────────────────────────────────────────

// One thread: a comment with its writer's picture, every change a dot on a
// faded line, one person's changes in one sitting grouped and folded when
// there are many; an empty value set to empty is no change.
record.thread = (frm) => {
	const feed = frm.page.wrapper[0].querySelector(".one-panel .new-timeline");
	const info = frm.get_docinfo ? frm.get_docinfo() : null;
	const list = feed && feed.querySelector(".timeline-items:not(.timeline-actions)");
	if (!list || !info) return;
	const doctype = frm.doctype;
	const blank = (value) => value === null || value === undefined || value === "" || value === 0 || value === "0";
	const label = (field, table) => __(frappe.meta.get_label(table || doctype, field) || field);
	const show = (field, value, table) => {
		const df = frappe.meta.get_docfield(table || doctype, field);
		if (blank(value)) return `<i>${__("empty")}</i>`;
		return esc(df ? $("<div>").html(frappe.format(value, df, { inline: true, only_value: true })).text() : value).slice(0, 60);
	};
	const LONG = ["Text Editor", "Text", "Small Text", "Long Text", "HTML Editor", "Markdown Editor", "Code", "JSON"];
	const events = [];
	(info.versions || []).forEach((version) => {
		let data = {};
		try {
			data = JSON.parse(version.data);
		} catch (e) {
			data = {};
		}
		const lines = [];
		let verb = "";
		(data.changed || []).forEach(([field, before, after]) => {
			if (blank(before) && blank(after)) return;
			if (field === "docstatus") {
				verb = after == 1 ? "submitted" : after == 2 ? "cancelled" : "draft";
				return;
			}
			const df = frappe.meta.get_docfield(doctype, field);
			if (!df || df.hidden) return;
			if (LONG.includes(df.fieldtype)) lines.push(`<span class="one-ch-field">${esc(label(field))}</span>${__("edited")}`);
			else lines.push(`<span class="one-ch-field">${esc(label(field))}</span>${show(field, before)}<span class="one-ch-arrow">→</span>${show(field, after)}`);
		});
		(data.row_changed || []).forEach(([table, idx, , changes]) => {
			const child = (frappe.meta.get_docfield(doctype, table) || {}).options;
			(changes || []).forEach(([field, before, after]) => {
				if (!(blank(before) && blank(after)))
					lines.push(`<span class="one-ch-field">${esc(label(table))} ${idx}: ${esc(label(field, child))}</span>${show(field, before, child)}<span class="one-ch-arrow">→</span>${show(field, after, child)}`);
			});
		});
		const rows = {};
		(data.added || []).forEach(([table]) => ((rows[table] = rows[table] || [0, 0])[0] += 1));
		(data.removed || []).forEach(([table]) => ((rows[table] = rows[table] || [0, 0])[1] += 1));
		Object.entries(rows).forEach(([table, [added, removed]]) => {
			const said = [added && (added === 1 ? __("1 row added") : __("{0} rows added", [added])), removed && (removed === 1 ? __("1 row removed") : __("{0} rows removed", [removed]))]
				.filter(Boolean)
				.join(", ");
			lines.push(`<span class="one-ch-field">${esc(label(table))}</span>${said}`);
		});
		if (lines.length || verb) events.push({ kind: "change", owner: version.owner, at: version.creation, lines, verb });
	});
	(info.comments || []).forEach((comment) => events.push({ kind: "comment", owner: comment.owner, at: comment.creation, html: comment.content }));
	(info.additional_timeline_content || []).forEach((item) => item.content && events.push({ kind: "told", at: item.creation, html: item.content, icon: item.icon }));
	const doc = frm.doc;
	events.push({ kind: "made", owner: doc.owner, at: doc.creation });
	events.sort((a, b) => (a.at < b.at ? 1 : -1));
	const groups = [];
	events.forEach((event) => {
		const last = groups[groups.length - 1];
		if (event.kind === "change" && last && last.kind === "change" && last.owner === event.owner && Math.abs(new Date(last.at) - new Date(event.at)) < 36e5) {
			last.lines.push(...event.lines);
			last.verb = last.verb || event.verb;
		} else groups.push({ ...event, lines: [...(event.lines || [])] });
	});
	const who = (user) => esc(frappe.user.full_name(user));
	const SAID = {
		made: (n, mine) => (mine ? __("{0} created this", [n], "Said of the reader") : __("{0} created this", [n])),
		commented: (n, mine) => (mine ? __("{0} commented", [n], "Said of the reader") : __("{0} commented", [n])),
		submitted: (n, mine) => (mine ? __("{0} submitted this", [n], "Said of the reader") : __("{0} submitted this", [n])),
		cancelled: (n, mine) => (mine ? __("{0} cancelled this", [n], "Said of the reader") : __("{0} cancelled this", [n])),
		draft: (n, mine) => (mine ? __("{0} returned this to draft", [n], "Said of the reader") : __("{0} returned this to draft", [n])),
		one: (n, mine) => (mine ? __("{0} changed 1 field", [n], "Said of the reader") : __("{0} changed 1 field", [n])),
		many: (n, mine, count) => (mine ? __("{0} changed {1} fields", [n, count], "Said of the reader") : __("{0} changed {1} fields", [n, count])),
	};
	const said_by = (user, kind, count) => SAID[kind](`<b>${who(user)}</b>`, user === frappe.session.user, count);
	const mark = (inner) => `<div class="one-act-mark">${inner}</div>`;
	const dot = mark(`<span class="one-act-dot"></span>`);
	const html = groups
		.map((group) => {
			const when = `<span class="one-act-when">${comment_when(group.at)}</span>`;
			if (group.kind === "told") return `<div class="one-act is-told">${group.icon ? mark(frappe.utils.icon(group.icon, "xs")) : dot}<div class="one-act-body"><div class="one-act-head">${when}${group.html}</div></div></div>`;
			if (group.kind === "made") return `<div class="one-act">${dot}<div class="one-act-body"><div class="one-act-head">${said_by(group.owner, "made")}${when}</div></div></div>`;
			if (group.kind === "comment")
				return `<div class="one-act is-comment">${mark(frappe.avatar(group.owner, "avatar-xs"))}<div class="one-act-body"><div class="one-act-head">${said_by(group.owner, "commented")}${when}</div><div class="one-act-comment">${group.html}</div></div></div>`;
			const count = group.lines.length;
			const open = count <= 3;
			const said = said_by(group.owner, group.verb || (count === 1 ? "one" : "many"), count);
			if (!count) return `<div class="one-act">${dot}<div class="one-act-body"><div class="one-act-head">${said}${when}</div></div></div>`;
			return `<div class="one-act is-group ${open ? "is-open" : ""}">${dot}<div class="one-act-body"><button type="button" class="one-act-head one-act-toggle" aria-expanded="${open}">${said}<span class="one-act-chev">${frappe.utils.icon("chevron-right", "xs")}</span>${when}</button><div class="one-act-lines">${group.lines.map((line) => `<div class="one-ch">${line}</div>`).join("")}</div></div></div>`;
		})
		.join("");
	list.innerHTML = `<div class="one-acts">${html}</div>`;
	$(list)
		.off("click.one-act")
		.on("click.one-act", ".one-act-toggle", (e) => {
			const act = e.currentTarget.closest(".one-act");
			act.classList.toggle("is-open");
			e.currentTarget.setAttribute("aria-expanded", act.classList.contains("is-open"));
		});
	feed.querySelector(".activity-title")?.classList.add("one-gone");
};

// The thread follows frappe's timeline: each time it is drawn, ours is.
$(document).on("form-refresh", (_e, frm) => {
	if (!onedesk.interface.uses("thread") || !frm.timeline) return;
	const proto = Object.getPrototypeOf(frm.timeline);
	if (Object.hasOwn(proto, "one_thread")) return;
	proto.one_thread = true;
	const render = proto.render_timeline_items;
	proto.render_timeline_items = function (...args) {
		const said = render.apply(this, args);
		const frm = this.frm;
		if (frm && onedesk.interface.uses("thread")) setTimeout(() => record.thread(frm), 0);
		return said;
	};
	frm.timeline.refresh();
});

// ── A list ──────────────────────────────────────────────────────────────

frappe.provide("onedesk.interface.list");
const list = onedesk.interface.list;

// The icon a kind of record is shown with: its module's declared icon, else
// the one its row on the rail carries (frappe's module sidebars).
onedesk.interface.icon_of = (doctype) => {
	if (frappe.boot.one_icons?.doctypes[doctype]) return frappe.boot.one_icons.doctypes[doctype];
	let found = null;
	const walk = (node, depth) => {
		if (found || !node || typeof node !== "object" || depth > 6) return;
		if (Array.isArray(node)) return node.forEach((one) => walk(one, depth + 1));
		if (node.link_type === "DocType" && node.link_to === doctype && node.icon) found = node.icon;
		for (const key of Object.keys(node)) if (key !== "parent") walk(node[key], depth + 1);
	};
	const sidebars = frappe.boot.module_sidebars || {};
	const current = frappe.app && frappe.app.sidebar && frappe.app.sidebar.current_module;
	walk(current && sidebars[current], 0);
	walk(sidebars, 0);
	return found;
};

// Over the rows: the list's icon and name, then a strip of the
// states its module declares (status by default), each a filter. The list's
// quick filters sit beside Filter in the actions row.
list.FAMILY = ["List", "Report", "Kanban", "Gantt", "Calendar", "Image", "Map", "Dashboard"];
// Views whose own body already sorts by state: a board's columns are its
// states, and a dashboard's charts count its own.
list.STATELESS = ["Kanban", "Dashboard"];

// A tree and a query report wear the same head with their own name (`title`),
// the icon of the doctype they show (`icon`), their own primary button's word
// (`rename: false`), their whole filter form in the row (`form: true`) and
// a report's own buttons at the head's far end (`actions: true`).
list.strip = async (view, with_states = true, how = {}) => {
	const doctype = view.doctype;
	const main = view.page.wrapper[0].querySelector(".layout-main-list") || (view.$frappe_list && view.$frappe_list[0].parentElement) || (view.page.main && view.page.main[0]);
	if (!main) return;
	let hero = main.querySelector(":scope > .one-hero-list");
	if (!hero) {
		hero = document.createElement("div");
		hero.className = "one-hero one-hero-list";
		hero.innerHTML = `<div class="one-hero-title"><span class="one-hero-icon" hidden></span><h1></h1></div>`;
		main.prepend(hero);
	}
	hero.querySelector("h1").textContent = how.title || __(doctype);
	list.place(view, hero, how.rename !== false, how.actions);
	const kind = (how.icon || doctype) && onedesk.interface.icon_of(how.icon || doctype);
	const mark = hero.querySelector(".one-hero-icon");
	mark.hidden = !kind;
	if (kind && mark.dataset.icon !== kind) {
		mark.innerHTML = frappe.utils.icon(kind, "md");
		mark.dataset.icon = kind;
	}
	list.filters(view, how.form);
	if (!with_states) {
		main.querySelector(":scope > .one-strip")?.remove();
		return;
	}
	const decl = (declared(doctype) || {}).states || { field: "status", order: [], hide: [], kinds: [] };
	if (decl.kinds && decl.kinds.length) return list.kinds(view, hero, decl.kinds);
	let states = [];
	if (frappe.meta.get_docfield(doctype, decl.field)) {
		try {
			states = await frappe.xcall("frappe.desk.listview.get_group_by_count", { doctype, current_filters: [], field: decl.field });
		} catch (e) {
			states = [];
		}
	}
	const total = states.reduce((sum, one) => sum + (one.count || 0), 0) || view.data.length;
	states = states.filter((one) => one.name && !decl.hide.includes(one.name));
	const rank = (one) => (decl.order.includes(one.name) ? decl.order.indexOf(one.name) : decl.order.length);
	states.sort((a, b) => rank(a) - rank(b) || b.count - a.count);
	let strip = main.querySelector(":scope > .one-strip");
	if (!states.length) {
		if (strip) strip.remove();
		return;
	}
	if (!strip) {
		strip = document.createElement("div");
		strip.className = "one-strip";
		hero.after(strip);
	}
	const on = ((view.filter_area && view.filter_area.get()) || []).find((one) => one[1] === decl.field && one[2] === "=");
	const item = (value, text, count) =>
		`<button type="button" class="one-strip-item${(on ? on[3] === value : !value) ? " is-on" : ""}" data-value="${esc(value)}"><span class="one-strip-label">${esc(text)}</span><span class="one-strip-count">${count}</span></button>`;
	strip.querySelectorAll(".one-strip-item").forEach((one) => one.remove());
	strip.insertAdjacentHTML("afterbegin", item("", __("All"), total) + states.map((one) => item(one.name, __(one.name), one.count)).join(""));
	strip.querySelectorAll(".one-strip-item").forEach((button) => {
		button.onclick = async () => {
			await view.filter_area.remove(decl.field);
			if (button.dataset.value) await view.filter_area.add([[doctype, decl.field, "=", button.dataset.value]]);
		};
	});
};

// A strip of kinds, each a set of filters rather than one field's value
// (registry "kinds"): counted, shown in their order, and one chosen at a time.
list.kinds = async (view, hero, kinds) => {
	const doctype = view.doctype;
	const main = hero.parentElement;
	const fields = [...new Set(kinds.flatMap((kind) => kind.filters.map((rule) => rule[0])))];
	const counts = await Promise.all(
		[[], ...kinds.map((kind) => kind.filters)].map((filters) => frappe.xcall("frappe.client.get_count", { doctype, filters }).catch(() => null))
	);
	const set = ((view.filter_area && view.filter_area.get()) || []).filter((one) => fields.includes(one[1]));
	const same = (rule, one) => one[1] === rule[0] && one[2] === rule[1] && String(one[3] ?? "") === String(rule[2] ?? "");
	const at = kinds.findIndex((kind) => kind.filters.length === set.length && kind.filters.every((rule) => set.some((one) => same(rule, one))));
	let strip = main.querySelector(":scope > .one-strip");
	if (!strip) {
		strip = document.createElement("div");
		strip.className = "one-strip";
		hero.after(strip);
	}
	const item = (index, text, count) =>
		`<button type="button" class="one-strip-item${index === at ? " is-on" : ""}" data-kind="${index}"><span class="one-strip-label">${esc(text)}</span>${count === null ? "" : `<span class="one-strip-count">${count}</span>`}</button>`;
	strip.querySelectorAll(".one-strip-item").forEach((one) => one.remove());
	strip.insertAdjacentHTML("afterbegin", item(-1, __("All"), counts[0]) + kinds.map((kind, i) => item(i, __(kind.label), counts[i + 1])).join(""));
	strip.querySelectorAll(".one-strip-item").forEach((button) => {
		button.onclick = async () => {
			const kind = kinds[Number(button.dataset.kind)];
			const kept = (view.filter_area.get() || []).filter((one) => !fields.includes(one[1]));
			await view.filter_area.clear(false);
			await view.filter_area.add([...kept, ...((kind && kind.filters) || []).map((rule) => [doctype, ...rule])]);
		};
	});
};

// The same head over an island's own list (the kit's interfaceHeading): its
// icon and name, a quieter word after it, New beside it, its ways of looking
// at the far end and a strip of states under it, drawn as a frappe list's
// are so the look dresses both alike. Said again, drawn again; said empty,
// gone. `ways` and `states` are [{ value, label, icon?, count? }]; a
// `primary` with a `menu` ([{ label, icon, onclick }]) opens it.
onedesk.interface.heading = (win, spec) => {
	const main = win && win.page && win.page.main && win.page.main[0];
	if (!main) return;
	main.querySelectorAll(":scope > .one-hero-island, :scope > .one-strip-island").forEach((one) => one.remove());
	if (!spec) return;
	const island = main.querySelector(":scope > .one-island") || main.firstElementChild;
	const hero = document.createElement("div");
	hero.className = "one-hero one-hero-list one-hero-island";
	hero.innerHTML = `<div class="one-hero-title"><span class="one-hero-icon"${spec.icon ? "" : " hidden"}></span><h1></h1></div>`;
	hero.querySelector("h1").textContent = spec.title || "";
	if (spec.icon) hero.querySelector(".one-hero-icon").innerHTML = frappe.utils.icon(spec.icon, "md");
	const title = hero.querySelector(".one-hero-title");
	if (spec.quiet) title.insertAdjacentHTML("beforeend", `<span class="one-hero-quiet">${esc(spec.quiet)}</span>`);
	if (spec.primary) {
		const group = document.createElement("span");
		group.className = "one-interface-group";
		group.dataset.tour = "interface-new";
		const $new = $(frappe.ui.button({ label: spec.primary.label, icon: "plus", variant: "solid", css_class: "primary-action", onclick: spec.primary.menu ? null : spec.primary.click }));
		$(group).append($new);
		if (spec.primary.menu) new frappe.ui.Dropdown({ trigger: $new, options: spec.primary.menu.map((one) => ({ label: one.label, icon: one.icon, onclick: one.onclick })) });
		title.append(group);
	}
	if (spec.ways && spec.ways.length) {
		const ways = document.createElement("span");
		ways.className = "one-interface-ways";
		ways.dataset.tour = "interface-ways";
		$(ways).append(
			frappe.ui.tab_buttons({
				type: "ghost",
				label: spec.ways_label || __("View"),
				value: spec.way,
				options: spec.ways.map((one) => ({ value: one.value, icon: one.icon, label: one.label, title: one.label })),
				on_change: (value) => spec.pick_way && spec.pick_way(value),
			})
		);
		hero.append(ways);
	}
	main.insertBefore(hero, island);
	if (!spec.states || !spec.states.length) return;
	const strip = document.createElement("div");
	strip.className = "one-strip one-strip-island";
	strip.setAttribute("role", "tablist");
	strip.innerHTML = spec.states
		.map(
			(one) =>
				`<button type="button" role="tab" aria-selected="${one.value === spec.state}" class="one-strip-item${one.value === spec.state ? " is-on" : ""}" data-value="${esc(one.value)}"><span class="one-strip-label">${esc(one.label)}</span>${one.count == null ? "" : `<span class="one-strip-count">${one.count}</span>`}</button>`
		)
		.join("");
	strip.querySelectorAll(".one-strip-item").forEach((button) => {
		button.onclick = () => button.dataset.value !== spec.state && spec.pick_state && spec.pick_state(button.dataset.value);
	});
	main.insertBefore(strip, island);
};

// The heading row holds what acts on the whole list: New beside the name,
// the ways of looking at the far end. The Frame keeps both by reference, so
// they go on working where they are put.
list.place = (view, hero, rename = true, actions_of = false) => {
	const win = view.page.interface;
	const title = hero.querySelector(".one-hero-title");
	const primary = win.group("primary")[0];
	if (primary && primary.parentElement !== title) title.append(primary);
	const label = primary && primary.querySelector(".primary-action .es-button__label.hidden-xs");
	if (rename && label && label.textContent.trim() !== __("New")) {
		label.closest(".primary-action").setAttribute("title", label.textContent.trim());
		label.textContent = __("New");
	}
	const ways = win.ways_slot()[0];
	if (ways && ways.parentElement !== hero) hero.append(ways);
	const actions = actions_of && view.page.custom_actions && view.page.custom_actions[0];
	if (actions && actions.parentElement !== hero) {
		actions.classList.add("one-hero-actions");
		hero.append(actions);
	}
};

// frappe's quick filters, in the row under the address, Filter and Sort at its end.
// A board keeps Filter and Group in a row of its own beside its quick
// filters, so that row follows them.
list.filters = (view, form = false) => {
	const wrapper = view.page.wrapper[0];
	const views = wrapper.querySelector(".page-head .one-interface-views");
	if (!views) return;
	const filters = form ? view.page.page_form && view.page.page_form[0] : wrapper.querySelector(".standard-filter-section");
	const board = wrapper.querySelector(".kanban-v2-filter-section");
	if (board && board.parentElement !== views) views.prepend(board);
	if (!filters) return;
	filters.classList.add("one-head-filters");
	if (filters.parentElement !== views || (board && filters.nextElementSibling !== board)) views.prepend(filters);
	// frappe's phone ID box is one more field: it starts the fields' strip
	// rather than standing between them and Filter, which on a phone took a
	// second row; where the ID is one of them already, it goes
	const id = wrapper.querySelector(".page-head .one-interface-filters > .mobile-id-filter");
	if (id) {
		filters.prepend(id);
		const field = id.querySelector("[data-fieldname]")?.dataset.fieldname;
		id.hidden = !!field && [...filters.children].some((el) => el !== id && el.dataset.fieldname === field);
	}
};

// The icons a module declares for its fields, on the list's column heads,
// drawn again whenever the list is.
list.icons = (view) => {
	const reg = declared(view.doctype) || {};
	const named = {};
	frappe.get_meta(view.doctype).fields.forEach((df) => {
		const name = (reg.fields && reg.fields[df.fieldname]) || onedesk.interface.field_icon(df);
		if (name) named[__(df.label)] = name;
	});
	view.$result[0].querySelectorAll(".list-row-head .list-row-col span, .list-row-head .list-row-col").forEach((el) => {
		const name = named[(el.textContent || "").trim()];
		if (name && !el.querySelector(".one-ico") && el.children.length === 0) el.insertAdjacentHTML("afterbegin", icon(name));
	});
};

// A view's … menu ends the address row, after search and a record's ‹ ›.
{
	const Frame = onedesk.interface.Frame;
	if (Frame && !Object.hasOwn(Frame.prototype, "one_look")) {
		Frame.prototype.one_look = true;
		const view = Frame.prototype.view;
		// A record's commands join the address row when they fit beside an
		// address still readable (220px), as a browser's toolbar does; else they
		// keep their own row under it. Measured from what is there, both ways.
		Frame.prototype.one_join = function (head) {
			const content = head.querySelector(".page-head-content");
			const form = this.$wrapper.attr("data-one-view") === "form";
			if (!content || !form) return this.$wrapper.removeClass("one-head-joined");
			const width = (el) => (el && el.offsetParent ? el.getBoundingClientRect().width : 0);
			const extra = content.querySelector(":scope > .standard-items-section");
			// a record's commands stand by its name, out of the address row
			if (!head.contains(this.$commands[0])) return this.$wrapper.addClass("one-head-joined");
			// what the parts need, not what a row stretched them to
			const own = (el) => (el ? [...el.children].reduce((sum, child) => sum + width(child) + 6, 0) : 0);
			const deep = (el) => (el ? [...el.children].reduce((sum, child) => sum + (child.children.length && !child.matches("button, .btn, .es-button") ? own(child) : width(child) + 6), 0) : 0);
			const needed =
				width(this.$nav[0]) + 220 + deep(this.$commands[0]) + (extra && extra.querySelector(".btn:not(.hide), .es-button:not(.hide)") ? deep(extra) : 0) +
				width(this.$tools[0]) + 40;
			this.$wrapper.toggleClass("one-head-joined", needed <= content.clientWidth);
		};
		Frame.prototype.view = function (parts = {}) {
			const said = view.call(this, parts);
			if (onedesk.interface.uses("head")) {
				const menu = this.group("menu");
				if (menu[0].parentElement !== this.$tools[0] || menu[0].nextElementSibling) this.$tools.append(menu);
				// the view's menu is three dots stood on end, the address row's last word
				menu[0].querySelectorAll('.menu-more-button use[href="#icon-ellipsis"]').forEach((use) => use.setAttribute("href", "#icon-ellipsis-vertical"));
				if (parts.menu && parts.menu.dropdown) parts.menu.dropdown.align = "end";
				// the head says its own height, so what sticks under it sits right
				// whether its commands fit the address row or wrap under it
				const head = this.$wrapper.find(".page-head")[0];
				if (head && !this.one_measured && window.ResizeObserver) {
					this.one_measured = new ResizeObserver(() => {
						this.one_join(head);
						if (head.offsetHeight && head.offsetHeight !== this.one_head_height) {
							this.one_head_height = head.offsetHeight;
							this.$wrapper[0].style.setProperty("--page-head-height", `${head.offsetHeight}px`);
						}
					});
					this.one_measured.observe(head);
					this.one_measured.observe(this.$commands[0]);
				}
			}
			return said;
		};
	}
}

{
	// Every way of looking at a list wears the list's head: its name with
	// New, the ways at the far end, the quick filters under the address.
	// The states strip is left off a board and a dashboard.
	// The report view draws itself without the list's after_render, and the
	// board is frappe's own page rather than a list view, so each is wrapped.
	const head = (view, states, how) => {
		if (!view.page || !view.page.interface) return;
		if (onedesk.interface.uses("strip")) list.strip(view, states, how);
		if (onedesk.interface.uses("icons") && view.view_name === "List") list.icons(view);
	};
	[frappe.views && frappe.views.ListView, frappe.views && frappe.views.ReportView].forEach((View) => {
		if (!View || Object.hasOwn(View.prototype, "one_look")) return;
		View.prototype.one_look = true;
		const after = View.prototype.after_render;
		View.prototype.after_render = function (...args) {
			const said = after.apply(this, args);
			if (list.FAMILY.includes(this.view_name)) head(this, !list.STATELESS.includes(this.view_name));
			return said;
		};
	});
	// A tree is a list drawn as its parents and children: its name (Chart of
	// Accounts), Add as New, its ways, its search in the row under the address.
	const Tree = frappe.views && frappe.views.TreeView;
	if (Tree && !Object.hasOwn(Tree.prototype, "one_look")) {
		Tree.prototype.one_look = true;
		// After frappe's primary button, and again after a tree's own
		// post_render, which may set it anew (Account's says Add Account).
		const tree_head = (tree) => head(tree, false, { title: tree.opts.title || __(tree.doctype) });
		["set_primary_action", "post_render"].forEach((name) => {
			const own = Tree.prototype[name];
			Tree.prototype[name] = function (...args) {
				const said = own.apply(this, args);
				tree_head(this);
				return said;
			};
		});
	}
	// A query report has no New and no ways: the head is its name, with the
	// icon of the doctype it reports on, and its filters fill the row.
	const Query = frappe.views && frappe.views.QueryReport;
	if (Query && !Object.hasOwn(Query.prototype, "one_look")) {
		Query.prototype.one_look = true;
		const page_head = Query.prototype.setup_page_head;
		Query.prototype.setup_page_head = function (...args) {
			const said = page_head.apply(this, args);
			head(this, false, { title: __(this.report_name), icon: this.report_doc && this.report_doc.ref_doctype, rename: false, form: true, actions: true });
			return said;
		};
	}
	onedesk.interface.when(frappe.views, "KanbanV2Page", (Board) => {
		if (Object.hasOwn(Board.prototype, "one_look")) return;
		Board.prototype.one_look = true;
		const quick = Board.prototype.setup_quick_filters;
		Board.prototype.setup_quick_filters = function (...args) {
			const said = quick.apply(this, args);
			head(this, false);
			return said;
		};
	});
}
