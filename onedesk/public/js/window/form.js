// A form on the window (docs/WINDOW.md): frappe's Form, saying what it has
// through `window.view`. Its one main action leads the command row as New
// does on a list (frappe's Save, Submit or Update; when frappe has none, the
// record's own solid button, such as Record Payment), its other buttons
// follow, then frappe's menu. Cancel stays at the row's far end. The ‹ › to
// the record before and after go beside Up, the tabs are the row under the
// commands, and who edited it last is the status.
onedesk.window.adapt("form", () => {
	const Form = frappe.ui.form && frappe.ui.form.Form;
	if (!Form || Object.hasOwn(Form.prototype, "one_window")) return;
	Form.prototype.one_window = true;
	const setup = Form.prototype.setup;
	Form.prototype.setup = function (...args) {
		const said = setup.apply(this, args);
		const win = this.page && this.page.window;
		if (win) {
			win.view({
				kind: "form",
				primary: this.page.btn_primary,
				commands: this.page.custom_actions,
				menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown },
				steps: this.page.icon_group,
				refresh: () => !this.is_new() && this.reload_doc(),
				up: () => frappe.set_route("List", this.doctype),
			});
		}
		return said;
	};

	const Layout = frappe.ui.form.Layout;
	if (Layout && !Object.hasOwn(Layout.prototype, "one_window")) {
		Layout.prototype.one_window = true;
		const tabbed = Layout.prototype.setup_tabbed_layout;
		Layout.prototype.setup_tabbed_layout = function (...args) {
			const said = tabbed.apply(this, args);
			const win = this.frm && this.frm.page && this.frm.page.window;
			const $list = this.page.children(".form-tabs-list");
			if (win && $list.length) {
				win.view({ row: $list });
				onedesk.window.tabs($list);
			}
			return said;
		};
	}

	const Sidebar = frappe.ui.form.Sidebar;
	if (Sidebar && !Object.hasOwn(Sidebar.prototype, "one_window")) {
		Sidebar.prototype.one_window = true;
		const refresh = Sidebar.prototype.refresh;
		Sidebar.prototype.refresh = function (...args) {
			const said = refresh.apply(this, args);
			const win = this.frm.page && this.frm.page.window;
			if (win) win.view({ status: onedesk.window.edited(this.frm.doc) });
			return said;
		};
	}
});

// Who made a record and who changed it last, for the status row.
onedesk.window.edited = (doc) => {
	if (!doc || doc.__islocal) return "";
	const by = (user) => frappe.user.full_name(user) || user;
	const created = __("Created {0} by {1}", [frappe.datetime.prettyDate(doc.creation), by(doc.owner)]);
	if (!doc.modified || doc.modified === doc.creation) return created;
	return [__("Edited {0} by {1}", [frappe.datetime.prettyDate(doc.modified), by(doc.modified_by)]), created].join(" · ");
};

// A form's tabs on one row: those that do not fit fold into More at its end,
// and the tab you are on is always shown.
onedesk.window.tabs = ($list) => {
	const $ul = $list.children(".form-tabs");
	const $more = $(
		`<li class="nav-item dropdown one-tabs-more"><button class="one-tabs-more-button" type="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">${__("More")} ${frappe.utils.icon("chevron-down", "xs")}</button><div class="dropdown-menu dropdown-menu-right"></div></li>`
	);
	const fold = () => {
		$more.appendTo($ul).hide();
		const $tabs = $ul.children(".nav-item").not($more).removeClass("one-folded");
		const room = $ul[0].clientWidth;
		if (!room || $ul[0].scrollWidth <= room) return;
		$more.show();
		const shown = $tabs.toArray().filter((li) => $(li).css("display") !== "none");
		const active = shown.find((li) => $(li).find(".nav-link.active").length);
		let used = $more.outerWidth(true) + (active ? $(active).outerWidth(true) : 0);
		const folded = [];
		for (const li of shown) {
			if (li === active) continue;
			const width = $(li).outerWidth(true);
			if (!folded.length && used + width <= room) used += width;
			else folded.push(li);
		}
		$(folded).addClass("one-folded");
		$more.find(".dropdown-menu").empty().append(
			folded.map((li) =>
				$(`<a class="dropdown-item" href="#"></a>`)
					.text($(li).find(".nav-link").text().trim())
					.on("click", (e) => {
						e.preventDefault();
						$(li).find(".nav-link").trigger("click");
					})
			)
		);
	};
	const later = () => requestAnimationFrame(fold);
	new ResizeObserver(later).observe($list[0]);
	// A tab made active (from More, or by frappe) is shown: watched on the
	// links, which folding never touches.
	new MutationObserver((changes) => changes.some((one) => one.target.classList.contains("nav-link")) && later()).observe($ul[0], {
		subtree: true,
		attributes: true,
		attributeFilter: ["class"],
	});
	$(document).on("form-refresh", later);
};
