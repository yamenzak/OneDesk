// ShortcutCenter (docs/READY.md, mechanism 19; one/shortcut_center.py): what
// each key does, where, in every app or in one, on a picture of a keyboard
// and a mouse. Choosing a shortcut lights its keys; Change listens for the
// next keys pressed, or keys clicked on the picture (a modifier clicked stays
// held until a key is clicked), or a mouse button clicked. A key another
// shortcut has where this one works is offered to move, and what the reader
// moved goes back with Reset.
onedesk.centers.declare("shortcuts", {
	help: ["One", "shortcuts"],
	css: "one-keys",
	sections(ctx) {
		const { module } = ctx;
		const S = onedesk.shortcuts;
		const kit = onedesk.centers.kit;
		const esc = frappe.utils.escape_html;
		// The window's keys are One's: the same in every app.
		const app_of = (one) => (one.module === onedesk.names.of("one_interface") ? "One" : one.module);
		const apps = [...new Set(S.all().map(app_of))].sort((a, b) => (a === "One" ? -1 : b === "One" ? 1 : a.localeCompare(b)));

		// ── The picture ─────────────────────────────────────────────────────
		// A key's width in quarters of a key: a row of the main block is sixty.
		const F = Array.from({ length: 12 }, (_, i) => [`F${i + 1}`, 4]);
		const letters = (codes) => codes.split(" ").map((one) => [one.length === 1 ? `Key${one}` : one, 4]);
		const MAIN = [
			[["Escape", 4], ["gap", 4], ...F.slice(0, 4), ["gap", 2], ...F.slice(4, 8), ["gap", 2], ...F.slice(8)],
			[["Backquote", 4], ...letters("Digit1 Digit2 Digit3 Digit4 Digit5 Digit6 Digit7 Digit8 Digit9 Digit0 Minus Equal"), ["Backspace", 8]],
			[["Tab", 6], ...letters("Q W E R T Y U I O P BracketLeft BracketRight"), ["Backslash", 6]],
			[["CapsLock", 7], ...letters("A S D F G H J K L Semicolon Quote"), ["Enter", 9]],
			[["ShiftLeft", 9], ...letters("Z X C V B N M Comma Period Slash"), ["ShiftRight", 11]],
			[["ControlLeft", 5], ["MetaLeft", 5], ["AltLeft", 5], ["Space", 30], ["AltRight", 5], ["MetaRight", 5], ["ControlRight", 5]],
		];
		const SIDE = [
			[["Home", 4], ["PageUp", 4], ["gap", 4]],
			[["End", 4], ["PageDown", 4], ["Delete", 4]],
			[["gap", 12]],
			[["gap", 4], ["ArrowUp", 4], ["gap", 4]],
			[["ArrowLeft", 4], ["ArrowDown", 4], ["ArrowRight", 4]],
		];
		// The keys a modifier is held on, as the engine names it.
		const MOD_OF = {
			ControlLeft: S.mac ? null : "mod",
			ControlRight: S.mac ? null : "mod",
			MetaLeft: S.mac ? "mod" : null,
			MetaRight: S.mac ? "mod" : null,
			AltLeft: "alt",
			AltRight: "alt",
			ShiftLeft: "shift",
			ShiftRight: "shift",
		};
		const CAP = {
			ControlLeft: S.mac ? "⌃" : "Ctrl",
			ControlRight: S.mac ? "⌃" : "Ctrl",
			MetaLeft: S.mac ? "⌘" : "Win",
			MetaRight: S.mac ? "⌘" : "Win",
			AltLeft: S.mac ? "⌥" : "Alt",
			AltRight: S.mac ? "⌥" : "Alt",
			ShiftLeft: S.mac ? "⇧" : "Shift",
			ShiftRight: S.mac ? "⇧" : "Shift",
			Backspace: S.mac ? "⌫" : "Backspace",
			CapsLock: "Caps",
			Space: "",
		};
		const cap = (code) => (code in CAP ? CAP[code] : S.key_label(code));
		const row = (keys) =>
			`<div class="one-kb-row">${keys
				.map(([code, span]) =>
					code === "gap"
						? `<span class="one-kb-gap" style="grid-column: span ${span}"></span>`
						: `<button type="button" class="one-kb-key${MOD_OF[code] ? " one-kb-mod" : ""}" data-code="${code}" style="grid-column: span ${span}" tabindex="-1"><span>${esc(cap(code))}</span></button>`
				)
				.join("")}</div>`;
		// The mouse: its body and two buttons, the wheel between them and the two
		// buttons on its thumb side, the three that can be given a shortcut.
		const MOUSE = `<svg class="one-mouse" viewBox="0 0 64 104" role="img" aria-label="${esc(__("Mouse"))}">
			<path class="one-mouse-shell" d="M32 3C15 3 8 16 8 34v36c0 19 10 31 24 31s24-12 24-31V34C56 16 49 3 32 3Z"/>
			<path class="one-mouse-line" d="M8 40h48M32 3v37"/>
			<rect class="one-kb-key" data-code="mouse:middle" x="27.5" y="12" width="9" height="18" rx="4.5"><title>${esc(S.key_label("mouse:middle"))}</title></rect>
			<rect class="one-kb-key" data-code="mouse:forward" x="3" y="46" width="8" height="15" rx="3"><title>${esc(S.key_label("mouse:forward"))}</title></rect>
			<rect class="one-kb-key" data-code="mouse:back" x="3" y="64" width="8" height="15" rx="3"><title>${esc(S.key_label("mouse:back"))}</title></rect>
		</svg>`;
		const picture = () =>
			$(`<div class="one-kb-wrap">
				<div class="one-kb">
					<div class="one-kb-main">${MAIN.map(row).join("")}</div>
					<div class="one-kb-side">${SIDE.map(row).join("")}</div>
					${MOUSE}
				</div>
				<div class="one-kb-said" aria-live="polite"></div>
			</div>`);

		// Which keys of the picture a key combination presses.
		const codes_of = (combo) => {
			const parts = combo.split("+");
			const key = parts.pop();
			const held = Object.entries(MOD_OF)
				.filter(([, mod]) => mod && parts.includes(mod))
				.map(([code]) => code);
			return [...held, key];
		};

		// ── One app's part ──────────────────────────────────────────────────
		const part = (app, panel) => {
			const $body = panel.body.empty();
			const WHERE = ["anywhere", "lists", "record", "calendar"];
			const rank = (one) => [apps.indexOf(app_of(one)), WHERE.includes(one.where) ? WHERE.indexOf(one.where) : WHERE.length];
			const mine = S.all()
				.filter((one) => !app || app_of(one) === app)
				.sort((a, b) => {
					const [x, y] = [rank(a), rank(b)];
					return x[1] - y[1] || x[0] - y[0];
				});
			const $kb = picture().appendTo($body);
			const $said = $kb.find(".one-kb-said");
			const $keys = $kb.find("[data-code]");
			const key = (code) => $keys.filter((_, el) => el.dataset.code === code);

			// The keys this part uses, marked; one shortcut's keys, lit.
			const mark = () => {
				$keys.removeClass("is-used");
				for (const one of mine) for (const combo of S.keys(one)) key(combo.split("+").pop()).addClass("is-used");
			};
			const light = (combos = []) => {
				$keys.removeClass("is-lit");
				for (const combo of combos) for (const code of codes_of(combo)) key(code).addClass("is-lit");
			};
			const say = (html = "") => $said.html(html);

			// Change: what is pressed or clicked next. A modifier clicked on the
			// picture is held until a key is clicked.
			let listening = null;
			const stop = () => {
				if (!listening) return;
				listening.$row.removeClass("is-listening");
				listening = null;
				S.recording = false;
				$kb.removeClass("is-listening");
				$keys.removeClass("is-held");
				light();
				say();
			};
			const take = async (combo) => {
				const { one, $row } = listening;
				if (S.reserved(combo)) {
					say(`${S.kbd(combo)} <span>${esc(__("belongs to your browser, so it can't be a shortcut."))}</span>`);
					return;
				}
				const other = S.clashes(combo, one);
				stop();
				if (other.length) {
					const them = other.map((it) => `<b>${esc(it.label)}</b> (${esc(it.where_label)})`).join(", ");
					light([combo]);
					say(`${S.kbd(combo)} <span>${__("is already {0}.", [them])}</span>`);
					const $use = kit.button({ label: __("Use It Here"), variant: "solid" }).appendTo($said);
					const $no = kit.button({ label: __("Cancel"), variant: "ghost" }).appendTo($said);
					$no.on("click", () => (light(), say()));
					$use.on("click", async () => {
						for (const it of other) await S.set(it, S.keys(it).filter((k) => k !== combo));
						await S.set(one, [combo]);
						kit.saved();
						draw();
					});
					return;
				}
				await S.set(one, [combo]);
				kit.saved();
				draw();
				$row && light([combo]);
			};
			const listen = (one, $row) => {
				stop();
				listening = { one, $row, held: new Set() };
				S.recording = true;
				$row.addClass("is-listening");
				$kb.addClass("is-listening");
				say(`<span>${esc(__("Press the keys for {0}, or click them on the keyboard or the mouse.", [one.label]))}</span>`);
				kit.button({ label: __("No Shortcut"), variant: "ghost" })
					.on("click", async () => {
						stop();
						await S.set(one, []);
						kit.saved();
						draw();
					})
					.appendTo($said);
				kit.button({ label: __("Cancel"), variant: "ghost" }).on("click", stop).appendTo($said);
			};

			const pressed = (e) => {
				if (!listening) return;
				if (e.key === "Escape" && !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey) {
					e.preventDefault();
					e.stopPropagation();
					return stop();
				}
				const combo = S.combo(e);
				// what is held so far, lit as it is pressed
				const down = { mod: e.ctrlKey || e.metaKey, alt: e.altKey, shift: e.shiftKey };
				$keys.removeClass("is-lit");
				for (const [c, m] of Object.entries(MOD_OF)) if (m && down[m]) key(c).addClass("is-lit");
				if (!combo) return;
				e.preventDefault();
				e.stopPropagation();
				take(combo);
			};
			document.addEventListener("keydown", pressed, true);
			panel.dialog.$wrapper.one("hidden.bs.modal", () => {
				document.removeEventListener("keydown", pressed, true);
				S.recording = false;
			});

			$keys.on("click", (e) => {
				const code = e.currentTarget.dataset.code;
				if (!listening) {
					const using = mine.filter((one) => S.keys(one).some((combo) => combo.split("+").pop() === code));
					light(using.flatMap((one) => S.keys(one).filter((combo) => combo.split("+").pop() === code)));
					say(using.length ? using.map((one) => `${S.kbd(S.keys(one).find((combo) => combo.split("+").pop() === code))} <span>${esc(one.label)}</span>`).join(" · ") : `<span>${esc(__("Nothing here uses this key."))}</span>`);
					return;
				}
				const mod = MOD_OF[code];
				if (mod) {
					listening.held.has(mod) ? listening.held.delete(mod) : listening.held.add(mod);
					$keys.removeClass("is-held");
					for (const [c, m] of Object.entries(MOD_OF)) if (m && listening.held.has(m)) key(c).addClass("is-held");
					return;
				}
				if (code.startsWith("Control") || code.startsWith("Meta")) return;
				const combo = [...["mod", "alt", "shift"].filter((m) => listening.held.has(m)), code].join("+");
				if (combo === "mouse:middle") return say(`<span>${esc(__("Hold another key with the middle button. Alone, it opens a link in a new tab."))}</span>`);
				take(combo);
			});

			// The list: grouped by where each works.
			const $list = $(`<div class="one-set-list one-keys-list"></div>`).appendTo($body);
			const draw = () => {
				$list.empty();
				const groups = new Map();
				for (const one of mine) {
					const where = one.where_label;
					if (!groups.has(where)) groups.set(where, []);
					groups.get(where).push(one);
				}
				for (const [where, list] of groups) {
					$list.append(`<div class="one-keys-where">${esc(where)}</div>`);
					for (const one of list) {
						const keys = S.keys(one);
						const shown = keys.length ? keys.map((combo) => S.kbd(combo)).join(`<span class="one-keys-or">${esc(__("or"))}</span>`) : `<span class="one-keys-none">${esc(__("No shortcut"))}</span>`;
						const $row = kit.row({ lead: "", title: one.label }).addClass("one-keys-row").appendTo($list);
						const $end = $row.find(".one-set-end").append(`<span class="one-keys-now">${shown}</span>`);
						if (S.moved(one)) {
							kit.button({ variant: "ghost", icon: "rotate-ccw", title: __("Back to {0}", [one.keys.map(S.label).join(", ") || __("No shortcut")]) })
								.on("click", async (e) => {
									e.stopPropagation();
									await S.reset(one);
									kit.saved();
									draw();
								})
								.appendTo($end);
						}
						kit.button({ label: __("Change"), variant: "outline" })
							.on("click", (e) => {
								e.stopPropagation();
								listen(one, $row);
							})
							.appendTo($end);
						$row.on("mouseenter", () => !listening && light(S.keys(one))).on("mouseleave", () => !listening && light());
					}
				}
				mark();
			};
			draw();

			// Every shortcut of the part as shipped again.
			const $reset = panel.$header.find(".one-keys-reset");
			$reset.toggleClass("hide", !mine.some(S.moved));
		};

		const tab = (app) => ({
			id: app ? `app:${app}` : "all",
			label: app ? app : __("Everything"),
			icon: app ? null : "keyboard",
			icon_html: app ? onedesk.centers.app_icon(app, "keyboard") : null,
			title: app ? app : __("Everything"),
			description: app
				? __("What each key does in {0}. What you change here is yours alone.", [app])
				: __("What each key does in every app. What you change here is yours alone."),
			/** The picture of a keyboard and a mouse beside the shortcuts, the
			 * keys lit as one is chosen and listened for as it changes: no
			 * declared kind draws a keyboard. */
			render(panel) {
				if (!panel.$header.find(".one-keys-reset").length) {
					kit.button({ label: __("Reset All"), variant: "ghost" })
						.addClass("one-keys-reset hide")
						.on("click", async () => {
							for (const one of S.all().filter((it) => (!app || app_of(it) === app) && S.moved(it))) await S.reset(one);
							kit.saved();
							panel.refresh();
						})
						.appendTo(panel.$header.find(".settings-dialog-panel-title"));
				}
				part(app, panel);
			},
		});

		const tabs = module
			? [{ items: [tab(module === onedesk.names.of("one_interface") ? "One" : module)] }]
			: [{ items: [tab(null)] }, { group: __("Apps"), items: apps.map(tab) }];
		return tabs;
	},
});
