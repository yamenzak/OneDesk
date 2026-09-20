// Palettes, and their cards in frappe's own Switch Theme dialog.
//
// Two dimensions, kept apart because frappe already owns one of them:
// `data-theme-mode` is light/dark/automatic and persists in User.desk_theme;
// `data-one-theme` is which palette answers, and persists in user settings
// because desk_theme is a Select of exactly three values and widening it
// would be editing their schema.
//
// `fetch_themes` is a literal array in frappe, with no registry to add to — so
// ThemeSwitcher is subclassed rather than the file forked. The contract is one
// method returning [{name, label, info}].
frappe.provide("onedesk.theme");

onedesk.theme.STORE = "onedesk";
onedesk.theme.DEFAULT = "one";
// Light and dark are the cards; automatic is a checkbox under them, because it
// is a preference about the two rather than a third thing to look at.
onedesk.theme.MODES = ["light", "dark"];

// The standard palette carries no prefix — the product is One, so "One · Light"
// says the same word twice. A named palette prefixes its own name.
// frappe's is not offered: a tenant of One has no use for it.
onedesk.theme.palettes = {
	one: { label: "" },
};

onedesk.theme.apply = function (palette) {
	document.documentElement.setAttribute("data-one-theme", palette || onedesk.theme.DEFAULT);
};

onedesk.theme.current = function () {
	return document.documentElement.getAttribute("data-one-theme") || onedesk.theme.DEFAULT;
};

// Default first so nothing flashes, then whatever the reader last chose.
onedesk.theme.apply();
frappe.model?.user_settings
	?.get(onedesk.theme.STORE)
	.then((saved) => saved.palette && onedesk.theme.apply(saved.palette))
	.catch(() => {});

frappe.ui.ThemeSwitcher = class OneThemeSwitcher extends frappe.ui.ThemeSwitcher {
	// One card per palette and mode: "One · Dark" is a palette and a mode, and
	// the dialog is the only place both are chosen.
	fetch_themes() {
		this.themes = [];
		for (const [palette, spec] of Object.entries(onedesk.theme.palettes)) {
			for (const mode of onedesk.theme.MODES) {
				const named = __(mode[0].toUpperCase() + mode.slice(1));
				this.themes.push({
					name: `${palette}:${mode}`,
					label: spec.label ? `${spec.label} · ${named}` : named,
					info: spec.label || named,
				});
			}
		}
		return Promise.resolve(this.themes);
	}

	// Automatic is still frappe's mode; it just is not a card. Checking it
	// leaves the palette alone and hands the light/dark choice to the system.
	render() {
		super.render();
		this.$follow = $(`
			<label class="theme-follow">
				<input type="checkbox" />
				<span>${__("Follow my system")}</span>
			</label>
		`).appendTo(this.dialog.$body);

		const box = this.$follow.find("input");
		box.prop("checked", this.mode() === "automatic");
		box.on("change", () => {
			if (box.is(":checked")) return super.toggle_theme("automatic");
			super.toggle_theme(frappe.ui.get_current_theme() || "light");
		});
	}

	refresh() {
		super.refresh();
		this.current_theme = `${onedesk.theme.current()}:${this.mode()}`;
	}

	mode() {
		return document.documentElement.getAttribute("data-theme-mode") || "automatic";
	}

	// super builds the preview from `theme.name`: "automatic" picks the
	// two-window mockup, anything else becomes data-theme. Our names are
	// "palette:mode", so it is handed the mode and the palette is added to the
	// containers afterwards — each card then previews its own palette rather
	// than the default one.
	get_preview_html(theme) {
		const [palette, mode] = theme.name.split(":");
		const $card = super.get_preview_html({ ...theme, name: mode });

		$card.find(".theme-preview-container").attr("data-one-theme", palette);
		$card.toggleClass("selected", this.current_theme === theme.name);

		// super's handler closed over the shim, so it would switch the mode and
		// leave the palette behind.
		$card.off("click").on("click", () => {
			if (this.current_theme === theme.name) return;
			this.themes.forEach((one) => one.$html && one.$html.removeClass("selected"));
			$card.addClass("selected");
			this.toggle_theme(theme.name);
		});

		return $card;
	}

	toggle_theme(name) {
		const [palette, mode] = name.split(":");
		onedesk.theme.apply(palette);
		frappe.model.user_settings.save(onedesk.theme.STORE, "palette", palette);
		super.toggle_theme(mode);
		this.current_theme = name;
		this.$follow?.find("input").prop("checked", false);
	}
};
