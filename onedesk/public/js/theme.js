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
onedesk.theme.MODES = ["automatic", "light", "dark"];

// A palette ships a CSS block per mode; `css` is only a label for the reader.
onedesk.theme.palettes = {
	frappe: { label: __("Frappe"), css: "frappe's own" },
	one: { label: __("One"), css: "onedesk/public/css/theme.css" },
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
				this.themes.push({
					name: `${palette}:${mode}`,
					label: `${spec.label} · ${__(mode[0].toUpperCase() + mode.slice(1))}`,
					info: spec.label,
				});
			}
		}
		return Promise.resolve(this.themes);
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
	}
};
