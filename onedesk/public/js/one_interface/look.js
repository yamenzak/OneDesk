// The look (onedesk/one_interface/AGENTS.md, Looks): how the frame and
// frappe's own screens in it are drawn. A look is a stylesheet scoped to
// `data-one-look` on the page and a set of parts the renderer turns on for
// it; the screens underneath are frappe's and the same in every look. Theme
// (light, dark) and palette (the workspace's colour) ride on top of any look.
frappe.provide("onedesk.interface");

onedesk.interface.LOOKS = {
	// frappe's desk on the frame, as it was before Canvas
	classic: {},
	// the record and the list on a quiet canvas, each one sheet on it
	canvas: { head: true, strip: true, thread: true, quiet: true, icons: true },
};

onedesk.interface.look = () => {
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

onedesk.interface.palette = () => document.documentElement.dataset.onePalette || "";

const dress = (host) => {
	const shadow = host.shadowRoot;
	if (!shadow) return;
	if (!shadow.adoptedStyleSheets.includes(ISLAND_PALETTE)) shadow.adoptedStyleSheets = [...shadow.adoptedStyleSheets, ISLAND_PALETTE];
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
const declared = (doctype) => (frappe.boot.one_interface || {})[doctype] || null;
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
	const shown = !frm.is_new();
	container.classList.toggle("one-has-head", shown);
	let hero = container.one_hero;
	if (!hero) {
		hero = document.createElement("div");
		hero.className = "one-hero one-hero-record";
		hero.innerHTML = `<div class="one-hero-row"><div class="one-hero-face" hidden></div><div class="one-hero-main"><div class="one-hero-title"><h1></h1></div></div></div><div class="one-head-cards"></div>`;
		container.one_hero = hero;
	}
	if (hero.previousElementSibling !== pageHead) pageHead.after(hero);
	hero.hidden = !shown;
	if (!shown) return;

	// the tabs sit under the head
	const row = pageHead.querySelector(".one-interface-row");
	if (row) {
		row.classList.add("one-tabs-below");
		if (hero.nextElementSibling !== row) hero.after(row);
	}

	const title = hero.querySelector(".one-hero-title");
	const name = frm.doc[frm.meta.title_field] || frm.doc.name;
	title.querySelector("h1").textContent = name;
	const pill = pageHead.querySelector(".page-indicator-pill") || title.querySelector(".page-indicator-pill");
	if (pill && pill.parentElement !== title) title.append(pill);

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
	if (frm.doc.name && frm.doc.name !== name) {
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
		steps.forEach((step, i) => {
			const done = step.state === "done";
			const joined = done && steps[i + 1] && steps[i + 1].state === "done";
			track.insertAdjacentHTML(
				"beforeend",
				`<div class="one-track-step ${done ? "is-done" : "is-todo"}"><div class="one-track-mark"><span class="one-track-dot">${done ? frappe.utils.icon("check", "xs") : ""}</span>${i < steps.length - 1 ? `<span class="one-track-line ${joined ? "is-done" : ""}"></span>` : ""}</div><div class="one-track-text">${esc(step.label)}<small class="${step.state === "late" ? "is-late" : ""}">${esc(step.note || "")}</small></div></div>`
			);
		});
		(hero.querySelector(".one-hero-name") || title).after(track);
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
			return { title: named || one.label, value: one.value, tone: TONE[one.tone] || null, route: one.route };
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

	// print, like and OneCloud sit at the bar's end, before Cancel
	const commands = pageHead.querySelector(".one-interface-commands");
	const likes = container.querySelector(".form-sidebar .form-stats-likes");
	if (commands && likes) {
		commands.querySelectorAll(".one-bar-icons").forEach((old) => old !== likes && old.remove());
		likes.classList.add("one-bar-icons");
		if (likes.parentElement !== commands) commands.append(likes);
	}
};

// What a saved record holds is shown; an empty field that isn't asked for
// waits behind one button, a field's help is a mark beside its label, a
// section with nothing shown goes, and so does a tab.
record.show_empty = (count) => (count === 1 ? __("Show 1 Empty Field") : __("Show {0} Empty Fields", [count]));

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
			};
			(page.querySelector(".form-page") || page).append(more);
		}
		more.dataset.count = quiet;
		const open = (page.querySelector(".form-page") || page).classList.contains("one-open");
		more.textContent = open ? __("Hide Empty Fields") : record.show_empty(quiet);
	} else if (more) more.remove();

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

// The icons a module declares for a record type's tabs and fields.
record.icons = (frm) => {
	const reg = declared(frm.doctype);
	if (!reg) return;
	((frm.layout && frm.layout.tabs) || []).forEach((tab) => {
		const link = tab.tab_link && (tab.tab_link[0] || tab.tab_link).querySelector && (tab.tab_link[0] || tab.tab_link).querySelector(".nav-link");
		const name = reg.tabs && reg.tabs[tab.df.fieldname];
		if (name && link && !link.querySelector(".one-ico")) link.insertAdjacentHTML("afterbegin", icon(name).replace("one-ico", "one-ico one-tab-ico"));
	});
	Object.entries(reg.fields || {}).forEach(([field, name]) => {
		const control = frm.fields_dict[field];
		const label = control && control.$wrapper && control.$wrapper[0].querySelector(".control-label");
		if (label && !label.querySelector(".one-ico")) label.insertAdjacentHTML("afterbegin", icon(name));
	});
};

// A record's shortcuts are rows of the panel: their own icon, a plain label
// and a mark at the end for what happens (+ makes a record, an arrow opens a
// list, a chevron anything else).
record.shortcuts = (frm) => {
	const box = frm.page.wrapper[0].querySelector(".form-sidebar .user-actions");
	if (!box) return;
	const TRAIL = { new: "plus", list: "arrow-up-right" };
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
	if (onedesk.interface.uses("icons")) record.icons(frm);
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
				verb = after == 1 ? __("submitted this") : after == 2 ? __("cancelled this") : __("returned this to draft");
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
	const mark = (inner) => `<div class="one-act-mark">${inner}</div>`;
	const dot = mark(`<span class="one-act-dot"></span>`);
	const html = groups
		.map((group) => {
			const when = `<span class="one-act-when">${comment_when(group.at)}</span>`;
			if (group.kind === "made") return `<div class="one-act">${dot}<div class="one-act-body"><div class="one-act-head"><b>${who(group.owner)}</b> ${__("created this")}${when}</div></div></div>`;
			if (group.kind === "comment")
				return `<div class="one-act is-comment">${mark(frappe.avatar(group.owner, "avatar-xs"))}<div class="one-act-body"><div class="one-act-head"><b>${who(group.owner)}</b> ${__("commented")}${when}</div><div class="one-act-comment">${group.html}</div></div></div>`;
			const count = group.lines.length;
			const open = count <= 3;
			const said = group.verb || (count === 1 ? __("changed 1 field") : __("changed {0} fields", [count]));
			if (!count) return `<div class="one-act">${dot}<div class="one-act-body"><div class="one-act-head"><b>${who(group.owner)}</b> ${said}${when}</div></div></div>`;
			return `<div class="one-act is-group ${open ? "is-open" : ""}">${dot}<div class="one-act-body"><button type="button" class="one-act-head one-act-toggle" aria-expanded="${open}"><b>${who(group.owner)}</b> ${said}<span class="one-act-chev">${frappe.utils.icon("chevron-right", "xs")}</span>${when}</button><div class="one-act-lines">${group.lines.map((line) => `<div class="one-ch">${line}</div>`).join("")}</div></div></div>`;
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

// Over the rows: the list's name and how many, then a strip of the states
// its module declares (status by default), each a filter, with the list's
// quick filters at the strip's end.
list.strip = async (view) => {
	const doctype = view.doctype;
	const main = view.page.wrapper[0].querySelector(".layout-main-list") || (view.$frappe_list && view.$frappe_list[0].parentElement);
	if (!main) return;
	let hero = main.querySelector(":scope > .one-hero-list");
	if (!hero) {
		hero = document.createElement("div");
		hero.className = "one-hero one-hero-list";
		hero.innerHTML = `<div class="one-hero-title"><h1></h1><span class="one-hero-count"></span></div>`;
		main.prepend(hero);
	}
	hero.querySelector("h1").textContent = __(doctype);
	const decl = (declared(doctype) || {}).states || { field: "status", order: [], hide: [] };
	let states = [];
	if (frappe.meta.get_docfield(doctype, decl.field)) {
		try {
			states = await frappe.xcall("frappe.desk.listview.get_group_by_count", { doctype, current_filters: [], field: decl.field });
		} catch (e) {
			states = [];
		}
	}
	const total = states.reduce((sum, one) => sum + (one.count || 0), 0) || view.data.length;
	hero.querySelector(".one-hero-count").textContent = total;
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
	// the quick filters join the strip's end
	const filters = view.page.wrapper[0].querySelector(".standard-filter-section");
	if (filters && filters.parentElement !== strip) {
		filters.classList.add("one-strip-filters");
		strip.append(filters);
	}
};

// The icons a module declares for its fields, on the list's column heads,
// drawn again whenever the list is.
list.icons = (view) => {
	const reg = declared(view.doctype);
	if (!reg || !reg.fields) return;
	const named = {};
	frappe.get_meta(view.doctype).fields.forEach((df) => {
		if (reg.fields[df.fieldname]) named[__(df.label)] = reg.fields[df.fieldname];
	});
	view.$result[0].querySelectorAll(".list-row-head .list-row-col span, .list-row-head .list-row-col").forEach((el) => {
		const name = named[(el.textContent || "").trim()];
		if (name && !el.querySelector(".one-ico") && el.children.length === 0) el.insertAdjacentHTML("afterbegin", icon(name));
	});
};

{
	const ListView = frappe.views && frappe.views.ListView;
	if (ListView && !Object.hasOwn(ListView.prototype, "one_look")) {
		ListView.prototype.one_look = true;
		const after = ListView.prototype.after_render;
		ListView.prototype.after_render = function (...args) {
			const said = after.apply(this, args);
			if (this.page && this.page.interface && this.view_name === "List") {
				if (onedesk.interface.uses("strip")) list.strip(this);
				if (onedesk.interface.uses("icons")) list.icons(this);
			}
			return said;
		};
	}
}
