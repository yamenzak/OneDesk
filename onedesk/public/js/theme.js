// frappe.require asks for our files by their plain address, which Frappe Cloud
// serves as immutable for a year; boot carries each one's hash (one/stamp.py).
if (frappe.assets && !frappe.assets.__one_stamped) {
	frappe.assets.__one_stamped = true;
	const theirs = frappe.assets.bundled_asset.bind(frappe.assets);
	frappe.assets.bundled_asset = (path, is_rtl) => {
		const held = (frappe.boot.one_assets || {})[path];
		return held && !path.includes("?") ? `${path}?v=${held}` : theirs(path, is_rtl);
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
