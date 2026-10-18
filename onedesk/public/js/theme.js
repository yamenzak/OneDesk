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
