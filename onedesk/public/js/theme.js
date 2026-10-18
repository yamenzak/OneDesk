// frappe's own Switch Theme dialog, with Light and Dark as the cards and
// Automatic as a checkbox under them: following the system is a preference
// about the two rather than a third thing to look at.
//
// `fetch_themes` is a literal array in frappe, with no registry to add to — so
// ThemeSwitcher is subclassed rather than the file forked, and each method
// calls frappe's own.
frappe.ui.ThemeSwitcher = class OneThemeSwitcher extends frappe.ui.ThemeSwitcher {
	// `size: "large"` was sized for three cards in a row; ours are two.
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

	// Picking a card is a choice against the system.
	toggle_theme(name) {
		super.toggle_theme(name);
		this.$follow?.find("input").prop("checked", false);
	}
};
