// OneStudio's ControlCenter (docs/ONE.md, stage 3): Numbering, Printing and
// Approvals, how the workspace adapts what One makes (one_studio/control.py).
// For the workspace's administrators.
frappe.provide("onedesk.studio_control");

onedesk.StudioSection = class StudioSection extends onedesk.CenterSection {
	static API = "onedesk.one_studio.control.";
	static HERE = "onestudio";
	static LABEL = "ControlCenter";
	static theirs = (one) => one.standard === "Yes";

	static SHEET = 794;
	static PAGE = 1123;
	static sheet = (top, foot, scale, whole = false) =>
		`<!doctype html><html><head><style>html,body{margin:0;background:#fff;color:#111;font-family:sans-serif}` +
		`body{padding:24px;width:746px;transform:scale(${scale});transform-origin:0 0}img{max-width:100%}` +
		`.lines{height:48px;margin:16px 0;background:repeating-linear-gradient(to bottom,#e5e7eb 0,#e5e7eb 6px,transparent 6px,transparent 14px)}` +
		(whole ? `html{overflow:hidden}body{box-sizing:border-box;width:794px;height:1123px;padding:45px 53px;display:flex;flex-direction:column}.lines{flex:1;height:auto;margin:32px 0;background:repeating-linear-gradient(to bottom,#f3f4f6 0,#f3f4f6 4px,transparent 4px,transparent 22px)}` : "") +
		`</style></head><body>${top || ""}${foot === null ? "" : `<div class="lines"></div>${foot || ""}`}</body></html>`;
	static frame = (html, className) => {
		const it = document.createElement("iframe");
		it.className = className;
		it.setAttribute("sandbox", "");
		it.srcdoc = html;
		return it;
	};

	draw_numbering(data) {
		const esc = frappe.utils.escape_html;
		const again = () => this.key === "numbering" && this.open("numbering", { fresh: true });
		const naming = (doctype) => onedesk.doctype_settings.open(doctype, "naming", again);
		this.page.set_primary_action(__("Set Up Naming"), () => onedesk.numbering.set_up(naming), "plus");
		this.$content.html(`<div class="one-shell-section" data-list="numbering"></div>`);
		onedesk.shell.table(this.$content.find('[data-list="numbering"]'), {
			title: __("Numbering"),
			rows: data.rows || [],
			page_size: 100,
			icon: "hash",
			empty: __("No numbered records"),
			none: __("No matching records"),
			open: (one) => naming(one.doctype),
			columns: [
				{ label: __("Record Type"), fieldname: "label" },
				{ label: __("Naming Rule"), fieldname: "named_by" },
				{
					label: __("Series"),
					render: (one) =>
						one.series
							? `<samp>${esc(one.series)}</samp>` + (one.others ? " " + frappe.ui.badge.html({ label: __("+{0} more", [one.others]), theme: "gray" }) : "")
							: "",
				},
				{ label: __("Next"), render: (one) => (one.next ? `<samp>${esc(one.next)}</samp>` : "") },
				{ label: __("Document Naming Rules"), render: (one) => (one.rules ? esc(String(one.rules)) : "") },
			],
		});
	}

	draw_approvals(data) {
		const esc = frappe.utils.escape_html;
		this.page.set_primary_action(__("New Approval"), () => onedesk.approvals.create(), "plus");
		this.$content.html(`<div class="one-shell-section" data-list="approvals"></div>`);
		onedesk.shell.table(this.$content.find('[data-list="approvals"]'), {
			title: __("Approvals"),
			rows: data.rows || [],
			page_size: 100,
			icon: "route",
			empty: __("No approvals"),
			none: __("No matching approvals"),
			open: (one) => frappe.set_route("workflow-builder", one.name),
			columns: [
				{
					label: __("Approval"),
					render: (one) => esc(one.workflow_name || one.name) + (one.is_active ? " " + frappe.ui.badge.html({ label: __("Active"), theme: "green" }) : ""),
				},
				{ label: __("Record Type"), fieldname: "label" },
				{ label: __("Steps"), render: (one) => esc(String(one.steps)) },
			],
		});
	}

	draw_printing(data) {
		const esc = frappe.utils.escape_html;
		this.page.set_primary_action(__("New Letter Head"), () => this.letter_head(), "plus");
		const kinds = [...new Map((data.formats || []).map((one) => [one.doc_type, one.label])).entries()];
		this.$content.html(
			onedesk.shell.section(
				__("Letter Heads"),
				'<div class="one-print-heads"></div>'
			) +
				onedesk.shell.section(
					__("Print Formats"),
					'<div class="one-print-kinds"></div>'
				)
		);
		const $heads = this.$content.find(".one-print-heads");
		const heads = data.letter_heads || [];
		if (!heads.length) {
			$heads.html(onedesk.shell.empty(__("No letter heads"), null, { icon: "image" }));
		} else {
			const $grid = $('<div class="dts-pf-grid"></div>').appendTo($heads);
			heads.forEach((one) => $grid.append(this.letter_head_card(one)));
		}
		const $kinds = this.$content.find(".one-print-kinds");
		if (!kinds.length) {
			$kinds.html(onedesk.shell.empty(__("No print formats"), null, { icon: "printer" }));
			return;
		}
		frappe.require("doctype_settings.bundle.js", () => {
			onedesk.doctype_settings.adapt();
			const Panel = frappe.ui.SettingsDialogPanel;
			for (const [doctype, label] of kinds) {
				frappe.model.with_doctype(doctype, () => {
					const panel = new Panel({ hide() {} }, {});
					const set_view = panel.set_view.bind(panel);
					panel.set_view = (view) => set_view({ ...view, title: __(label), description: null });
					panel.$el.appendTo($kinds);
					frappe.doctype_settings.builders["print-format"](panel, doctype);
				});
			}
		});
	}

	letter_head_card(one) {
		const $card = $(`
			<div class="dts-pf-card${one.is_default ? " is-default" : ""}">
				<div class="dts-pf-preview">
					<div class="dts-pf-badge one-print-badges">${[
						StudioSection.theirs(one) ? frappe.ui.badge.html({ label: __("Standard"), theme: "gray" }) : "",
						one.disabled ? frappe.ui.badge.html({ label: __("Disabled"), theme: "gray" }) : "",
					].join("")}</div>
					<button type="button" class="dts-pf-star" data-selected="${one.is_default ? "true" : "false"}">${frappe.utils.icon("star", "sm")}</button>
					<div class="dts-pf-thumb"></div>
				</div>
				<div class="dts-pf-footer"><span class="dts-pf-name ellipsis"></span></div>
			</div>`);
		const $thumb = $card.find(".dts-pf-thumb");
		$card.find(".dts-pf-name").text(one.name).on("click", () => this.letter_head(one));
		$thumb.on("click", () => this.letter_head(one));
		const $star = $card.find(".dts-pf-star");
		if (one.is_default) {
			$star.attr("title", __("Default"));
		} else {
			$star.attr("title", __("Set as Default")).on("click", async (e) => {
				e.stopPropagation();
				await frappe.xcall("onedesk.one_studio.printing.save_letter_head", { values: { name: one.name, modified: one.modified, is_default: 1 } });
				frappe.show_alert({ message: __("Default updated"), indicator: "green" });
				this.refresh({ fresh: true });
			});
		}
		requestAnimationFrame(() => {
			const scale = ($thumb.width() || 200) / StudioSection.SHEET;
			$thumb.append(StudioSection.frame(StudioSection.sheet(one.drawn_top, one.drawn_foot || "", scale, true), "one-print-head-frame"));
		});
		return $card;
	}

	letter_head(one = null) {
		const theirs = !!one && StudioSection.theirs(one);
		const esc = frappe.utils.escape_html;
		const kept = one && one.one_top ? frappe.utils.parse_json(one.one_top) : null;
		let preset = one ? (kept && kept.preset) || null : "classic";
		const shows = (kept && kept.show) || ["address", "phone", "email", "website"];
		const kept_foot = one && one.one_foot ? frappe.utils.parse_json(one.one_foot) : null;
		let foot = one ? (kept_foot && kept_foot.preset) || (one.footer ? null : "none") : "centred";
		const foot_shows = (kept_foot && kept_foot.show) || ["phone", "website", "tax_id"];
		const SHOWN = [
			["name", __("Name")],
			["address", __("Address")],
			["phone", __("Phone")],
			["email", __("Email")],
			["website", __("Website")],
			["tax_id", __("Tax ID")],
		];
		const page = StudioSection.sheet;
		const frame = StudioSection.frame;
		const dialog = new frappe.ui.Dialog({
			title: one ? one.name : __("New Letter Head"),
			size: theirs ? "" : "extra-large",
			fields: [
				...(theirs ? [{ fieldtype: "HTML", fieldname: "theirs", options: frappe.ui.alert.html({ title: __("Standard Letter Head"), description: __("Only Default and Disabled can be changed on a standard letter head."), theme: "gray" }) }] : []),
				{ fieldtype: "Data", fieldname: "letter_head_name", label: __("Name"), reqd: 1, hidden: one ? 1 : 0 },
				{ fieldtype: "HTML", fieldname: "preview" },
				{ fieldtype: "Section Break" },
				{ fieldtype: "Check", fieldname: "is_default", label: __("Default"), description: __("Printed on a document unless another is chosen.") },
				{ fieldtype: "Check", fieldname: "disabled", label: __("Disabled") },
			],
			primary_action_label: one ? __("Update") : __("Create"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_studio.printing.save_letter_head", {
					values: {
						letter_head_name: values.letter_head_name,
						is_default: values.is_default,
						disabled: values.disabled,
						...(preset && !theirs ? { one_top: settings() } : {}),
						...(foot && !theirs ? (foot === "none" ? { one_foot: null, footer_source: "HTML", footer: "" } : { one_foot: foot_settings() }) : {}),
						name: one ? one.name : null,
						modified: one ? one.modified : null,
					},
				});
				dialog.hide();
				frappe.show_alert({ message: one ? __("Letter head updated") : __("Letter head created"), indicator: "green" });
				this.refresh({ fresh: true });
			},
		});
		const group = (fields) => {
			const made = new frappe.ui.FieldGroup({ body: document.createElement("div"), fields });
			made.make();
			return made;
		};
		const top_part = theirs
			? null
			: group([
					{ fieldtype: "HTML", fieldname: "presets" },
					{ fieldtype: "Section Break" },
					{
						fieldtype: "MultiCheck",
						fieldname: "show",
						label: __("Show"),
						columns: 2,
						sort_options: false,
						options: SHOWN.map(([value, label]) => ({ value, label, checked: shows.includes(value) ? 1 : 0 })),
						on_change: () => drawn(),
					},
					{ fieldtype: "Int", fieldname: "logo_height", label: __("Logo Height"), description: __("In pixels."), default: (kept && kept.logo_height) || 60, change: () => drawn() },
					{ fieldtype: "Check", fieldname: "line", label: __("Brand Line"), description: __("A line in the Brand Colour under the header."), default: kept && kept.line ? 1 : 0, change: () => drawn() },
					{ fieldtype: "Select", fieldname: "align", label: __("Logo Alignment"), options: [{ value: "left", label: __("Left") }, { value: "center", label: __("Centre") }, { value: "right", label: __("Right") }], default: (kept && kept.align) || "left", change: () => drawn() },
					{ fieldtype: "HTML", fieldname: "from_general", options: `<p class="text-muted small">${esc(__("The name, logo, address, contacts and colour come from One's ControlCenter, under Company and Branding."))}</p>` },
				]);
		const foot_part = theirs
			? null
			: group([
					{ fieldtype: "HTML", fieldname: "feet" },
					{ fieldtype: "Section Break", fieldname: "foot_settings" },
					{
						fieldtype: "MultiCheck",
						fieldname: "foot_show",
						label: __("Show"),
						columns: 2,
						sort_options: false,
						options: [["logo", __("Logo")], ...SHOWN].map(([value, label]) => ({ value, label, checked: foot_shows.includes(value) ? 1 : 0 })),
						on_change: () => drawn(),
					},
					{ fieldtype: "Data", fieldname: "foot_note", label: __("Note"), description: __("For example, a thank-you line."), default: (kept_foot && kept_foot.note) || "", change: () => drawn() },
					{ fieldtype: "Check", fieldname: "foot_line", label: __("Brand Line"), description: __("A line in the Brand Colour over the footer."), default: kept_foot && kept_foot.line ? 1 : 0, change: () => drawn() },
				]);
		const part = (fieldname) => (top_part.fields_dict[fieldname] ? top_part : foot_part);
		const parts = theirs
			? null
			: {
					get_value: (fieldname) => part(fieldname).get_value(fieldname),
					get_field: (fieldname) => part(fieldname).get_field(fieldname),
					set_df_property: (fieldname, property, value) => part(fieldname).set_df_property(fieldname, property, value),
			  };
		if (!theirs) {
			const tabs = new frappe.ui.Tabs({
				tabs: [
					{ label: __("Header"), content: $(top_part.body)[0] },
					{ label: __("Footer"), content: $(foot_part.body)[0] },
				],
			});
			const $studio = $(`<div class="one-lh-studio"><div class="one-lh-side"></div><div class="one-lh-stage"></div></div>`);
			$studio.find(".one-lh-side").append(tabs.$el);
			dialog.get_field("preview").$wrapper.empty().append($studio);
		}
		const settings = () => ({
			preset,
			show: parts.get_value("show") || [],
			logo_height: parts.get_value("logo_height"),
			align: parts.get_value("align"),
			line: parts.get_value("line") ? 1 : 0,
		});
		const foot_settings = () => ({
			preset: foot,
			show: parts.get_value("foot_show") || [],
			note: parts.get_value("foot_note") || "",
			line: parts.get_value("foot_line") ? 1 : 0,
		});
		const foot_html = () => {
			if (foot === "none") return "";
			const chosen = drawn_feet.find((d) => d.preset === foot);
			return chosen ? chosen.html : (one && one.drawn_foot) || "";
		};
		const show_preview = (top, bottom = foot_html()) => {
			const $stage = theirs ? dialog.get_field("preview").$wrapper : dialog.get_field("preview").$wrapper.find(".one-lh-stage");
			const scale = Math.min(1, (($stage.width() || 600) - 2) / StudioSection.SHEET, (window.innerHeight - 320) / StudioSection.PAGE);
			const sheet = frame(page(top, bottom, scale, true), "one-letter-head-sheet");
			sheet.style.height = `${Math.ceil(StudioSection.PAGE * scale) + 2}px`;
			sheet.style.width = `${Math.ceil(StudioSection.SHEET * scale) + 2}px`;
			$stage.empty().append(sheet);
		};
		let drawn_with = [];
		let drawn_feet = [];
		const cards = () => {
			const field = parts.get_field("presets");
			if (!field) return;
			const $grid = $(`<div class="one-lh-presets"></div>`);
			for (const one_preset of drawn_with) {
				const $card = $(`<button type="button" class="one-lh-preset"></button>`)
					.toggleClass("one-lh-preset--chosen", one_preset.preset === preset)
					.text(one_preset.label)
					.on("mouseenter", () => show_preview(one_preset.html))
					.on("mouseleave", () => shown())
					.on("click", () => {
						preset = one_preset.preset;
						cards();
						shown();
					});
				$grid.append($card);
			}
			const note = preset
				? ""
				: `<p class="text-muted small">${esc(__("This header is custom HTML. Choosing a preset replaces it."))}</p>`;
			field.$wrapper.empty().append(note).append($grid);
		};
		const feet = () => {
			const field = parts.get_field("feet");
			if (!field) return;
			const $grid = $(`<div class="one-lh-presets one-lh-presets--feet"></div>`);
			const top_now = () => (drawn_with.find((d) => d.preset === preset) || {}).html || (one && one.drawn_top);
			for (const one_foot of [...drawn_feet, { preset: "none", label: __("None"), html: "" }]) {
				const $card = $(`<button type="button" class="one-lh-preset"></button>`)
					.toggleClass("one-lh-preset--chosen", one_foot.preset === foot)
					.text(one_foot.label)
					.on("mouseenter", () => show_preview(top_now(), one_foot.html))
					.on("mouseleave", () => shown())
					.on("click", () => {
						foot = one_foot.preset;
						feet();
						shown();
					});
				$grid.append($card);
			}
			const note = foot
				? ""
				: `<p class="text-muted small">${esc(__("This footer is custom HTML. Choosing a preset replaces it."))}</p>`;
			field.$wrapper.empty().append(note).append($grid);
		};
		const shown = () => {
			if (theirs) return show_preview(one.drawn_top);
			parts.set_df_property("align", "hidden", preset !== "logo");
			for (const fieldname of ["foot_show", "foot_note", "foot_line"]) {
				parts.set_df_property(fieldname, "hidden", !foot || foot === "none");
			}
			const chosen = drawn_with.find((d) => d.preset === preset);
			show_preview(chosen ? chosen.html : one && one.drawn_top);
		};
		const drawn = frappe.utils.debounce(async () => {
			if (theirs) return shown();
			[drawn_with, drawn_feet] = await Promise.all([
				frappe.xcall("onedesk.one_studio.letter_heads.presets", { settings_of: settings() }),
				frappe.xcall("onedesk.one_studio.letter_heads.presets", { settings_of: foot_settings(), part: "foot" }),
			]);
			cards();
			feet();
			shown();
		}, 200);
		if (one) dialog.set_values({ letter_head_name: one.letter_head_name || one.name, is_default: one.is_default, disabled: one.disabled });
		if (one && !theirs) {
			dialog.set_secondary_action_label(__("Edit in Builder"));
			dialog.set_secondary_action(() => {
				dialog.hide();
				this.design_letter_head(one.name);
			});
			dialog.add_custom_action(__("Delete"), () =>
				frappe.confirm(__("Delete letter head {0}?", [one.name]), async () => {
					await frappe.xcall("frappe.client.delete", { doctype: "Letter Head", name: one.name });
					dialog.hide();
					this.refresh({ fresh: true });
				})
			);
		}
		dialog.show();
		drawn();
	}

	async design_letter_head(name) {
		const designer = await frappe.xcall("onedesk.one_studio.printing.design_letter_head", { letter_head: name });
		frappe.set_route("print-format-builder", designer);
	}
};

onedesk.studio_control.ABOUT = {
	numbering: __("How each kind of record is numbered."),
	printing: __("The letter heads and print formats documents are printed and sent on."),
	approvals: __("Who approves which records, step by step."),
};

onedesk.studio_control.open = ({ at = null } = {}) => {
	if (!frappe.boot.one_administers) return onedesk.account_center.open();
	const tabs = [
		["numbering", __("Numbering"), "hash"],
		["printing", __("Printing"), "printer"],
		["approvals", __("Approvals"), "route"],
	].map(([id, label, icon]) => onedesk.center_section.tab(onedesk.StudioSection, { id, label, icon, about: onedesk.studio_control.ABOUT[id] }));
	const dialog = onedesk.module_settings.open({ module: "OneStudio", tabs: [{ group: null, items: tabs }], default_tab: at });
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneStudio = onedesk.studio_control.open;

$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.interface.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== "OneStudio") return;
		win.module_foot({ module: "OneStudio", settings: () => onedesk.studio_control.open() });
		onedesk.interface.nav.place();
	}, 0)
);
