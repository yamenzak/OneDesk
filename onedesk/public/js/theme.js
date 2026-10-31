// frappe.require asks for our files by their plain address, which Frappe Cloud
// serves as immutable for a year; boot carries each one's hash (one/stamp.py).
// The hash goes on the URL, never the path: frappe reads a file's kind from
// the text after "?" in the path, so "x.js?v=1" would have no loader.
if (frappe.assets && !frappe.assets.__one_stamped) {
	frappe.assets.__one_stamped = true;
	const theirs = frappe.assets.load_asset.bind(frappe.assets);
	// An address frappe finds no loader for stopped the setup wizard on Frappe
	// Cloud: its kind is read from its path instead, or it is passed over.
	const loader = (path) => {
		const handlers = frappe.assets._handlers || {};
		const kind = new URL(path, window.location.origin).pathname.split(".").pop();
		return handlers[frappe.assets.extn(path)] ? null : handlers[kind] || "none";
	};
	frappe.assets.load_asset = (path, url) => {
		const own = loader(path);
		if (own === "none") {
			console.warn(`${path} is not a script or a stylesheet, so it was not loaded.`);
			return Promise.resolve();
		}
		if (own) {
			if (frappe.assets._executed.includes(path)) return Promise.resolve();
			return own(url).then(() => frappe.assets._executed.push(path));
		}
		const held = (frappe.boot.one_assets || {})[path];
		if (!held) return theirs(path, url);
		const stamped = new URL(url, window.location.origin);
		stamped.searchParams.set("v", held);
		return theirs(path, stamped.toString());
	};
}

frappe.ui.ThemeSwitcher = class OneThemeSwitcher extends frappe.ui.ThemeSwitcher {
	setup_dialog() {
		super.setup_dialog();
		this.dialog.$wrapper.find(".modal-dialog").removeClass("modal-lg");
	}

	fetch_themes() {
		return super.fetch_themes().then((themes) => {
			this.themes = themes.filter((one) => one.name !== "automatic");
			return this.themes;
		});
	}

	render() {
		super.render();
		this.$follow = $(`
			<label class="theme-follow">
				<input type="checkbox" />
				<span>${__("Follow my system")}</span>
			</label>
		`).appendTo(this.dialog.$body);

		const box = this.$follow.find("input");
		box.prop("checked", document.documentElement.getAttribute("data-theme-mode") === "automatic");
		box.on("change", () => {
			if (box.is(":checked")) return super.toggle_theme("automatic");
			super.toggle_theme(frappe.ui.get_current_theme() || "light");
		});
	}

	toggle_theme(name) {
		super.toggle_theme(name);
		this.$follow?.find("input").prop("checked", false);
	}
};
