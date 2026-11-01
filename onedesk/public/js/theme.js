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

// frappe's theme dialog, as One's Appearance: the theme (light, dark or the
// system's) and the palette (onedesk/one_interface/AGENTS.md, Palettes), each
// card a small picture of the window drawn from the same roles the window
// reads (.one-sample, tokens.css). A choice shows at once and is kept: the
// theme in frappe's own user field, the palette in the window's user settings.
frappe.ui.ThemeSwitcher = class OneThemeSwitcher extends frappe.ui.ThemeSwitcher {
	setup_dialog() {
		this.dialog = new frappe.ui.Dialog({ title: __("Appearance") });
		this.body = $(`<div class="one-appearance"></div>`).appendTo(this.dialog.$body);
		this.bind_events();
	}

	fetch_themes() {
		this.themes = [
			{ name: "light", label: __("Light") },
			{ name: "dark", label: __("Dark") },
			{ name: "automatic", label: __("System") },
		];
		return Promise.resolve(this.themes);
	}

	// the theme a picture is drawn in when the choice is the system's
	shown_theme() {
		if (this.current_theme !== "automatic") return this.current_theme;
		return frappe.ui.dark_theme_media_query.matches ? "dark" : "light";
	}

	sample(theme, palette) {
		const root = document.documentElement;
		const brand = root.dataset.oneFrame === "brand" ? root.style.getPropertyValue("--one-frame-brand") : "";
		const $sample = $(`
			<span class="one-sample" data-theme="${theme}" aria-hidden="true">
				<span class="one-sample-bar"></span>
				<span class="one-sample-window">
					<span class="one-sample-side"><i></i><i class="one-sample-on"></i><i></i><i></i></span>
					<span class="one-sample-canvas">
						<span class="one-sample-sheet"><i class="one-sample-title"></i><i></i><i></i><i class="one-sample-short"></i><b></b></span>
					</span>
				</span>
			</span>
		`);
		if (palette !== "standard") $sample.attr("data-one-palette", palette);
		if (brand) $sample.attr("data-one-frame", "brand").css("--one-frame-brand", brand);
		if (root.dataset.oneFrameInk) $sample.attr("data-one-frame-ink", root.dataset.oneFrameInk);
		return $sample;
	}

	card({ label, says, chosen, pictures, pick }) {
		const $card = $(`
			<button type="button" class="one-appearance-card" aria-pressed="${chosen}">
				<span class="one-appearance-picture"></span>
				<span class="one-appearance-label"></span>
			</button>
		`);
		$card.find(".one-appearance-picture").append(pictures);
		$card.find(".one-appearance-label").text(label);
		if (says) $(`<span class="one-appearance-says"></span>`).text(says).appendTo($card);
		$card.on("click", pick);
		return $card;
	}

	render() {
		this.body.empty();
		const palette = onedesk.interface.palette() || "standard";
		const group = (title) => {
			const $group = $(`<div class="one-appearance-group"><div class="one-appearance-head"></div><div class="one-appearance-row"></div></div>`).appendTo(this.body);
			$group.find(".one-appearance-head").text(title);
			return $group.find(".one-appearance-row");
		};

		const $themes = group(__("Theme"));
		for (const theme of this.themes) {
			const pictures = theme.name === "automatic" ? [this.sample("light", palette), this.sample("dark", palette).addClass("one-sample-half")] : [this.sample(theme.name, palette)];
			theme.$html = this.card({
				label: theme.label,
				chosen: this.current_theme === theme.name,
				pictures,
				pick: () => this.toggle_theme(theme.name),
			}).appendTo($themes);
		}

		const palettes = onedesk.interface.palettes();
		if (palettes.length < 2) return;
		const $palettes = group(__("Palette"));
		for (const name of palettes) {
			const one = onedesk.interface.PALETTES[name];
			this.card({
				label: one.label,
				says: one.says,
				chosen: palette === name,
				pictures: [this.sample(this.shown_theme(), name)],
				pick: () => {
					if (palette === name) return;
					onedesk.interface.set_palette(name, true);
					this.render();
				},
			}).appendTo($palettes);
		}
	}

	toggle_theme(theme) {
		if (this.current_theme === theme) return;
		this.current_theme = theme;
		document.documentElement.setAttribute("data-theme-mode", theme);
		frappe.xcall("frappe.core.doctype.user.user.switch_theme", { theme: toTitle(theme) });
		this.render();
	}
};
