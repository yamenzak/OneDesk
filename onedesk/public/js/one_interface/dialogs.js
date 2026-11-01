// One anatomy for every dialog (onedesk/one_interface/AGENTS.md, Dialogs).
// Frappe's own Dialog and SettingsDialog stay the engine; each is told its
// kind, and the kind decides its size and parts, never the caller:
//   ask    frappe.confirm, frappe.warn, frappe.prompt, onedesk.interface.ask
//   tell   frappe.msgprint
//   task   any other frappe.ui.Dialog
//   create the record drawer (window create, a creator)
//   centre a SettingsDialog with its rail
// The header says where you are and holds the window's controls (enlarge,
// close; a centre's Back is module_settings.js `view`); the footer says what is still needed on the left and
// holds the verbs on the right.
frappe.provide("onedesk.interface");

onedesk.interface.WINDOWED = ["task", "create", "centre"];

{
	const Dialog = frappe.ui.Dialog;
	if (Dialog && !Object.hasOwn(Dialog.prototype, "one_dialog")) {
		Dialog.prototype.one_dialog = true;
		const make = Dialog.prototype.make;
		Dialog.prototype.make = function (...args) {
			const said = make.apply(this, args);
			const centre = frappe.ui.SettingsDialog && this instanceof frappe.ui.SettingsDialog;
			const kind = this.one_kind || (centre ? "centre" : "task");
			this.one_mark(kind);
			// what is still needed, or what the verb will do, at the footer's start
			this.$one_need = $('<div class="one-dialog-need"></div>').prependTo(this.footer);
			return said;
		};

		// Kind is set again when a helper (confirm, msgprint) learns it after make.
		Dialog.prototype.one_mark = function (kind) {
			this.one_kind = kind;
			this.$wrapper.addClass("one-dialog").attr("data-kind", kind);
			// The kind is always told; only a look that draws dialogs adds controls.
			const windowed = onedesk.interface.WINDOWED.includes(kind) && onedesk.interface.uses("dialogs");
			const $actions = this.$wrapper.find(".modal-actions").first();
			if (windowed && !this.$one_enlarge) {
				this.$one_enlarge = $(frappe.ui.button.html({ icon: "maximize-2", variant: "ghost", title: __("Enlarge"), css_class: "icon-btn one-dialog-enlarge" }))
					.attr("aria-label", __("Enlarge"))
					.on("click", () => this.one_enlarge());
				// A centre draws no header of its own; its window controls sit in its
				// corner, after Help when the centre has one (module_settings.js).
				const centre = frappe.ui.SettingsDialog && this instanceof frappe.ui.SettingsDialog;
				if ($actions.length && !centre) $actions.prepend(this.$one_enlarge);
				else {
					const $close = $(frappe.ui.button.html({ icon: "x", variant: "ghost", title: __("Close"), css_class: "icon-btn" }))
						.attr("aria-label", __("Close"))
						.on("click", () => this.hide());
					$('<div class="one-dialog-controls"></div>').append(this.$one_enlarge, $close).appendTo(this.$wrapper.find(".modal-content").first());
				}
			}
			if (this.$one_enlarge) this.$one_enlarge.toggle(windowed);
			return this;
		};

		// Enlarged, a dialog fills the window, not the browser.
		Dialog.prototype.one_enlarge = function (on) {
			const now = on === undefined ? !this.$wrapper.hasClass("one-enlarged") : !!on;
			this.$wrapper.toggleClass("one-enlarged", now);
			if (this.one_keeps_size && on === undefined) onedesk.interface.keep(this.one_keeps_size, now ? 1 : 0);
			if (this.$one_enlarge) {
				const label = now ? __("Make Smaller") : __("Enlarge");
				this.$one_enlarge.attr({ title: label, "aria-label": label }).html(frappe.utils.icon(now ? "minimize-2" : "maximize-2", "sm"));
			}
		};

		Dialog.prototype.one_need = function (html) {
			if (this.$one_need) this.$one_need.html(html || "");
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
