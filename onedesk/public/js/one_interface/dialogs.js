// One anatomy for every dialog, in every look (onedesk/one_interface/AGENTS.md,
// Dialogs). Frappe's own Dialog and SettingsDialog stay the engine; each is
// told its kind, and the kind decides its size and parts, never the caller:
//   ask    frappe.confirm, frappe.warn, frappe.prompt, onedesk.interface.ask
//   tell   frappe.msgprint
//   task   any other frappe.ui.Dialog
//   create onedesk.interface.create
//   centre any other SettingsDialog
// The header says where you are and holds the window's controls, which only
// this file draws: Back (a panel one page deep, `panel.one_back`), Help
// (`dialog.one_help`), Enlarge and Close. The footer says what is still
// needed on the left (`dialog.one_need`) and holds the verbs on the right.
frappe.provide("onedesk.interface");

onedesk.interface.WINDOWED = ["task", "create", "centre"];

{
	const control = (icon, label, css = "") =>
		$(frappe.ui.button.html({ icon, variant: "ghost", title: label, css_class: `icon-btn ${css}` })).attr("aria-label", label);
	const railed = (dialog) => frappe.ui.SettingsDialog && dialog instanceof frappe.ui.SettingsDialog;

	const Dialog = frappe.ui.Dialog;
	if (Dialog && !Object.hasOwn(Dialog.prototype, "one_dialog")) {
		Dialog.prototype.one_dialog = true;
		const make = Dialog.prototype.make;
		Dialog.prototype.make = function (...args) {
			const said = make.apply(this, args);
			this.one_mark(this.one_kind || (railed(this) ? "centre" : "task"));
			this.$one_need = $('<div class="one-dialog-need"></div>').prependTo(this.footer);
			return said;
		};

		// The kind is set again when a helper (confirm, msgprint) learns it after make.
		Dialog.prototype.one_mark = function (kind) {
			this.one_kind = kind;
			this.$wrapper.addClass("one-dialog").attr("data-kind", kind);
			if (!this.$one_controls) {
				this.$one_enlarge = control("maximize-2", __("Enlarge"), "one-dialog-enlarge").on("click", () => this.one_enlarge());
				if (railed(this)) {
					// A dialog with a rail draws no header; its controls sit in its corner.
					this.$one_controls = $('<div class="one-dialog-controls"></div>')
						.append(this.$one_enlarge, control("x", __("Close")).on("click", () => this.hide()))
						.appendTo(this.$wrapper.find(".modal-content").first());
				} else {
					this.$one_controls = this.$wrapper.find(".modal-actions").first().prepend(this.$one_enlarge);
				}
			}
			this.$one_enlarge.toggle(onedesk.interface.WINDOWED.includes(kind) && !this.minimizable);
			// A centre opens at the size it was left at, in this browser.
			if (kind === "centre") this.one_enlarge(!!onedesk.interface.kept("centre_large", false), true);
			return this;
		};

		// Enlarged, a dialog fills the window, not the browser.
		Dialog.prototype.one_enlarge = function (on, quiet = false) {
			const now = on === undefined ? !this.$wrapper.hasClass("one-enlarged") : !!on;
			this.$wrapper.toggleClass("one-enlarged", now);
			if (this.one_kind === "centre" && !quiet) onedesk.interface.keep("centre_large", now ? 1 : 0);
			const label = now ? __("Make Smaller") : __("Enlarge");
			this.$one_enlarge.attr({ title: label, "aria-label": label }).html(frappe.utils.icon(now ? "minimize-2" : "maximize-2", "sm"));
			return this;
		};

		// Help for what is open, first among the window's controls.
		Dialog.prototype.one_help = function (open) {
			this.$one_controls.find(".one-dialog-help").remove();
			control("circle-question-mark", __("Help"), "one-dialog-help").on("click", open).prependTo(this.$one_controls);
			return this;
		};

		Dialog.prototype.one_need = function (html) {
			if (this.$one_need) this.$one_need.html(html || "");
			return this;
		};

		// A dialog with a rail says whether it shows it, and whether its body is
		// a few fields (small, as tall as they are) or more.
		Dialog.prototype.one_shape = function ({ rail = true, small = false } = {}) {
			this.$wrapper.attr({ "data-rail": rail ? "on" : "off", "data-size": small ? "small" : "full" });
			return this;
		};
	}

	// Back, before a panel's title, once it has gone a page deep. frappe's
	// set_header and set_view draw the title again, which takes Back away.
	const Panel = frappe.ui.SettingsDialogPanel;
	if (Panel && !Object.hasOwn(Panel.prototype, "one_back")) {
		Panel.prototype.one_back = function (go) {
			const $title = this.$header.find(".settings-dialog-panel-title").first();
			$title.find(".one-dialog-back").remove();
			control("arrow-left", __("Back"), "one-dialog-back").on("click", go).prependTo($title);
			return this;
		};
	}
}

// Ask: the question is the title when it is short enough to be one, with a
// round mark before it; the effect, when there is one, is the line under it.
{
	const wrap = (name, tone) => {
		const asked = frappe[name];
		if (!asked || asked.one_dialog) return;
		frappe[name] = function (message, ...rest) {
			const dialog = asked.call(this, message, ...rest);
			if (dialog && dialog.one_mark) {
				dialog.one_mark("ask").$wrapper.attr("data-tone", tone);
				onedesk.interface.lead(dialog, "circle-question-mark", typeof message === "string" ? message : "");
			}
			return dialog;
		};
		frappe[name].one_dialog = true;
	};
	wrap("confirm", "gray");
	wrap("warn", "red");
}

{
	const prompt = frappe.prompt;
	if (prompt && !prompt.one_dialog) {
		frappe.prompt = function (...args) {
			const dialog = prompt.apply(this, args);
			if (dialog && dialog.one_mark) dialog.one_mark("ask");
			return dialog;
		};
		frappe.prompt.one_dialog = true;
	}
}

// Tell: a message and OK, its mark red when it is an error.
{
	const msgprint = frappe.msgprint;
	if (msgprint && !msgprint.one_dialog) {
		frappe.msgprint = function (msg, ...rest) {
			const said = msgprint.call(this, msg, ...rest);
			const dialog = frappe.msg_dialog;
			if (dialog && dialog.one_mark) {
				const indicator = ($.isPlainObject(msg) && msg.indicator) || "blue";
				const tone = indicator === "red" ? "red" : indicator === "orange" || indicator === "yellow" ? "orange" : "gray";
				dialog.one_mark("tell").$wrapper.attr("data-tone", tone);
				onedesk.interface.lead(dialog, tone === "red" ? "circle-alert" : "info", "");
			}
			return said;
		};
		frappe.msgprint.one_dialog = true;
	}
}

// The round mark before an ask's or a tell's title, and a short plain
// question promoted to the title when frappe gave it a generic one.
const TONES = ["red", "orange", "yellow", "green", "blue", "gray", "grey", "purple", "pink", "cyan", "darkgrey", "lightblue"];
onedesk.interface.lead = (dialog, icon, message) => {
	const $title = dialog.$wrapper.find(".modal-title").first();
	const $section = $title.closest(".title-section");
	$section.find(".one-dialog-mark").remove();
	$section.prepend(`<span class="one-dialog-mark">${frappe.utils.icon(icon, "sm")}</span>`);
	// the mark carries the tone, so frappe's coloured dot before the title goes
	dialog.$wrapper.find(".modal-header .indicator").removeClass((i, names) =>
		names.split(" ").filter((name) => name === "indicator" || TONES.includes(name)).join(" ")
	);
	const plain = message && !/[<>]/.test(message) && message.length <= 120;
	if (plain && $title.text().trim() === __("Confirm", null, "Title of confirmation dialog")) {
		$title.text(message);
		dialog.$body.find(".frappe-confirm-message").remove();
	}
};

// The confirmation as it should be asked: the question, the effect, and a
// verb that names the act, red when it cannot be undone.
onedesk.interface.ask = ({ question, effect = "", verb, danger = false }) =>
	new Promise((resolve) => {
		let answered = false;
		const dialog = new frappe.ui.Dialog({
			one_kind: "ask",
			title: question,
			primary_action_label: verb,
			primary_action: () => {
				answered = true;
				dialog.hide();
				resolve(true);
			},
			secondary_action_label: __("Cancel"),
			secondary_action: () => dialog.hide(),
		});
		dialog.$wrapper.attr("data-tone", danger ? "red" : "gray");
		// frappe's own red button, as frappe.warn draws it
		if (danger) frappe.ui.button.dress(dialog.get_primary_btn(), { variant: "solid", theme: "red" });
		onedesk.interface.lead(dialog, danger ? "trash-2" : "circle-question-mark", "");
		if (effect) dialog.$body.append($('<p class="one-dialog-effect"></p>').text(effect));
		dialog.onhide = () => answered || resolve(false);
		dialog.show();
	});
