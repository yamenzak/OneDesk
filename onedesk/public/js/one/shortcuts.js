// The keys (docs/READY.md, mechanism 19; one/shortcut_center.py). Every module
// declares its shortcuts in its own shortcuts.py, and the code that does each
// says so here by its id (`onedesk.shortcuts.does`), so a module's screen
// registers what it does while it is open. A key runs the shortcut that
// belongs to the view in front of the reader: one made for that view before
// one that works anywhere. What the reader moved in ShortcutCenter is theirs.
//
// A key is its place on the keyboard (`event.code`), with the modifiers held
// in the order mod, alt, shift: "mod+KeyK", "shift+Slash", "KeyJ". `mod` is
// Ctrl, or Command on a Mac. A mouse's side buttons are "mouse:back" and
// "mouse:forward"; its middle button, "mouse:middle", only with a modifier,
// since alone it opens a link in a new tab.
frappe.provide("onedesk.shortcuts");

(() => {
	const S = onedesk.shortcuts;
	S.mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
	S.commands = S.commands || {};

	// What a shortcut does, by its id; returns a function that takes it back,
	// for a screen that is closed.
	S.does = (id, fn) => {
		S.commands[id] = fn;
		return () => {
			if (S.commands[id] === fn) delete S.commands[id];
		};
	};

	const boot = () => frappe.boot.one_shortcuts || { shortcuts: [], yours: {}, reserved: [] };
	S.all = () => boot().shortcuts;
	S.keys = (one) => (Object.hasOwn(boot().yours || {}, one.id) ? boot().yours[one.id] : one.keys);
	S.moved = (one) => Object.hasOwn(boot().yours || {}, one.id);
	S.reserved = (combo) => (boot().reserved || []).includes(combo);

	// The view in front of the reader: what the window says it is, and the
	// page it is on (a module's own screen is named by its page).
	S.here = () => {
		const wrapper = frappe.container && frappe.container.page;
		const kind = wrapper ? $(wrapper).find(".one-interface").addBack(".one-interface").attr("data-one-view") || "" : "";
		const route = frappe.get_route ? frappe.get_route() : [];
		return { kind, page: String(route[0] || "").toLowerCase() };
	};
	S.applies = (one, here = S.here()) => !one.kinds || one.kinds.includes(here.kind) || one.kinds.includes(`page:${here.page}`);

	const MODIFIERS = ["Control", "Meta", "Alt", "Shift", "AltGraph", "OS"];
	const held = (e) => [(e.ctrlKey || e.metaKey) && "mod", e.altKey && "alt", e.shiftKey && "shift"].filter(Boolean);
	S.combo = (e) => (!e.code || MODIFIERS.includes(e.key) ? null : [...held(e), e.code].join("+"));
	const BUTTONS = { 1: "mouse:middle", 3: "mouse:back", 4: "mouse:forward" };
	S.mouse_combo = (e) => (BUTTONS[e.button] ? [...held(e), BUTTONS[e.button]].join("+") : null);

	// The element really focused, inside an island's shadow root too.
	const focused = () => {
		let at = document.activeElement;
		while (at && at.shadowRoot && at.shadowRoot.activeElement) at = at.shadowRoot.activeElement;
		return at;
	};
	S.typing = () => {
		const at = focused();
		return !!at && (at.matches("input, select, textarea, [contenteditable=''], [contenteditable=true]") || at.isContentEditable);
	};
	const dialog_open = () => !!$(".modal.show:visible").length;

	// Every key to the shortcuts it can mean, built again when the reader
	// moves one.
	S.build = () => {
		const index = new Map();
		for (const one of S.all()) {
			for (const combo of S.keys(one)) {
				if (!index.has(combo)) index.set(combo, []);
				index.get(combo).push(one);
			}
		}
		S.index = index;
		// The keys frappe had, which a declaration took over, stay frappe's
		// no more: wherever they now go, they do only what ShortcutCenter says.
		S.folded = new Set(S.all().map((one) => one.frappe).filter(Boolean));
		for (const key of S.folded) frappe.ui.keys.off(key);
	};

	S.find = (combo, { typing = false, dialog = false, here = S.here() } = {}) => {
		const meant = (S.index && S.index.get(combo)) || [];
		const fits = meant.filter(
			(one) => S.applies(one, here) && (!typing || one.typing) && (!dialog || one.dialogs) && S.commands[one.id]
		);
		return fits.find((one) => one.kinds) || fits[0] || null;
	};

	S.run = (one, e) => {
		try {
			return S.commands[one.id](e);
		} catch (error) {
			console.error(error);
		}
	};

	const press = (e, combo) => {
		if (!combo || S.recording) return false;
		const one = S.find(combo, { typing: S.typing(), dialog: dialog_open() });
		if (!one) return false;
		e.preventDefault();
		e.stopPropagation();
		S.run(one, e);
		return true;
	};

	document.addEventListener("keydown", (e) => press(e, S.combo(e)), true);

	// A mouse button: the press runs it, and its release, which a browser
	// goes back or forward on, is kept from the browser.
	let swallow = false;
	document.addEventListener(
		"mousedown",
		(e) => {
			const combo = S.mouse_combo(e);
			if (!combo || (combo === "mouse:middle" && !held(e).length)) return;
			if (press(e, combo)) swallow = true;
		},
		true
	);
	for (const type of ["mouseup", "auxclick"]) {
		document.addEventListener(
			type,
			(e) => {
				if (!swallow || !BUTTONS[e.button]) return;
				e.preventDefault();
				e.stopPropagation();
				if (type === "auxclick" || e.button !== 1) swallow = false;
			},
			true
		);
	}

	// frappe registers its own keys as its views open (a form's Ctrl+P);
	// one a declaration took over is not registered again.
	const add = frappe.ui.keys.add_shortcut;
	frappe.ui.keys.add_shortcut = function (opts = {}) {
		if (S.folded && S.folded.has(opts.shortcut)) return;
		return add.call(this, opts);
	};

	// frappe's own list of shortcuts (Shift+/ and the user menu) is
	// ShortcutCenter, which shows what every key does and lets it move.
	frappe.ui.keys.show_keyboard_shortcut_dialog = () => onedesk.centers.open("shortcuts");

	// The words for a key: the reader's own keyboard's letter where the
	// browser says it, the key's name otherwise.
	const NAMES = {
		Space: () => __("Space"),
		Enter: () => __("Enter"),
		Escape: () => "Esc",
		Backspace: () => (S.mac ? "⌫" : __("Backspace")),
		Delete: () => (S.mac ? "⌦" : __("Delete")),
		Tab: () => "Tab",
		ArrowLeft: () => "←",
		ArrowRight: () => "→",
		ArrowUp: () => "↑",
		ArrowDown: () => "↓",
		PageUp: () => "PgUp",
		PageDown: () => "PgDn",
		Home: () => "Home",
		End: () => "End",
		CapsLock: () => "Caps",
		"mouse:back": () => __("Mouse Back"),
		"mouse:forward": () => __("Mouse Forward"),
		"mouse:middle": () => __("Middle Click"),
	};
	const US = {
		Slash: "/",
		Backslash: "\\",
		Comma: ",",
		Period: ".",
		Semicolon: ";",
		Quote: "'",
		Backquote: "`",
		BracketLeft: "[",
		BracketRight: "]",
		Minus: "-",
		Equal: "=",
	};
	S.layout = null;
	if (navigator.keyboard && navigator.keyboard.getLayoutMap) {
		navigator.keyboard
			.getLayoutMap()
			.then((map) => (S.layout = map))
			.catch(() => {});
	}
	S.key_label = (code) => {
		if (NAMES[code]) return NAMES[code]();
		const local = S.layout && S.layout.get(code);
		if (local && local.trim()) return local.length === 1 ? local.toUpperCase() : local;
		if (/^Key[A-Z]$/.test(code)) return code.slice(3);
		if (/^Digit\d$/.test(code)) return code.slice(5);
		if (/^Numpad/.test(code)) return code.replace("Numpad", "Num ");
		return US[code] || code;
	};
	const MOD_WORDS = () => ({ mod: S.mac ? "⌘" : "Ctrl", alt: S.mac ? "⌥" : "Alt", shift: S.mac ? "⇧" : "Shift" });
	S.parts = (combo) => {
		const words = MOD_WORDS();
		return combo.split("+").map((part) => words[part] || S.key_label(part));
	};
	S.kbd = (combo) => `<span class="one-combo">${S.parts(combo).map((part) => `<kbd>${frappe.utils.escape_html(part)}</kbd>`).join("")}</span>`;
	S.label = (combo) => S.parts(combo).join(S.mac ? "" : "+");

	// What a key already does where another shortcut would work: the
	// shortcuts it would take it from. One for anywhere meets every view.
	S.clashes = (combo, one) =>
		S.all().filter((other) => {
			if (other.id === one.id || !S.keys(other).includes(combo)) return false;
			if (!other.kinds || !one.kinds) return true;
			return other.kinds.some((kind) => one.kinds.includes(kind));
		});

	// Saved for the reader, and the keys built again at once.
	S.set = async (one, keys) => {
		boot().yours = await frappe.xcall("onedesk.one.shortcut_center.save", { id: one.id, keys: JSON.stringify(keys) });
		S.build();
	};
	S.reset = async (one = null) => {
		boot().yours = await frappe.xcall("onedesk.one.shortcut_center.reset", { id: one ? one.id : null });
		S.build();
	};

	// One's own: the centres and the shell.
	S.does("one.shortcuts", () => onedesk.centers.open("shortcuts"));
	S.does("one.home", () => frappe.set_route("one"));
	S.does("one.notifications", () => frappe.ui.sidebar_panels && frappe.ui.sidebar_panels.toggle("notifications"));
	S.does("one.theme", () => {
		if (frappe.theme_switcher && frappe.theme_switcher.dialog && frappe.theme_switcher.dialog.is_visible) return frappe.theme_switcher.hide();
		frappe.theme_switcher = new frappe.ui.ThemeSwitcher();
		frappe.theme_switcher.show();
	});

	$(document).on("startup", () => S.build());
	if (frappe.boot && frappe.boot.one_shortcuts) S.build();
})();
