const PORTAL_KINDS = [
	"Quotation",
	"Sales Order",
	"Delivery Note",
	"Sales Invoice",
	"Request for Quotation",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Invoice",
];

// The Portal dialog (one_portal/share.py), one for every place it opens: a
// sent or submitted record (who sees it, links to it), a customer or a
// supplier (its people), a contact (them). Each person is invited, invited
// again, revoked or restored where they are listed (one_portal/invite.py).
const portal_share = (name) => `onedesk.one_portal.share.${name}`;
const portal_invite = (name) => `onedesk.one_portal.invite.${name}`;

function portal_link_line(one) {
	if (one.state === "answered") return __("Answered by {0}, {1}", [one.used_by, one.used_on]);
	const opened =
		one.opened === 0 ? __("Not opened yet") : one.opened === 1 ? __("Opened once") : __("Opened {0} times", [one.opened]);
	return `${opened} · ${__("until {0}", [one.expires])}`;
}

function portal_person_line(one) {
	const where = {
		invited: __("Invited, not signed in yet"),
		active: __("Signed in {0}", [one.when]),
		revoked: __("Access revoked"),
		staff: __("Signs in to One"),
	}[one.status];
	return [one.email || __("No email"), where || __("Not on the portal")].join(" · ");
}

frappe.provide("onedesk.portal");

// OnePortal turned off in the app picker (one/apps.py) takes every Portal
// button with it; the server refuses the rest (one_portal/gate.py).
onedesk.portal.on = () => !((frappe.boot.one_hidden || {}).apps || []).includes("OnePortal");

// The Portal button, the same on every record: frappe's button in OnePortal's
// teal, with its mark (css/one_portal/button.css).
onedesk.portal.button = (frm, open) => {
	const $btn = frm.add_custom_button(__("Portal"), open);
	if (!$btn || $btn.attr("data-theme") === "teal") return $btn;
	$btn.attr("data-theme", "teal");
	$btn.find(".es-button__label").before(frappe.utils.icon("oneportal", "sm", "", "", "", true));
	return $btn;
};

onedesk.portal.open = async (doctype, name, after) => {
	const first = await frappe.xcall(portal_share("access"), { doctype, name });
	portal_dialog(doctype, name, first, after);
};

function portal_dialog(doctype, name, first, after) {
	const esc = frappe.utils.escape_html;
	const dialog = new frappe.ui.Dialog({
		title: __("{0} on the Portal", [first.title]),
		fields: [{ fieldtype: "HTML", fieldname: "body" }],
		primary_action_label: __("Done", null, "Close a dialog"),
		primary_action: () => dialog.hide(),
	});
	dialog.onhide = () => after && after();
	const $body = dialog.fields_dict.body.$wrapper;
	let said = first;

	const select = (css, options, disabled) =>
		`<div class="frappe-control ${css}" data-fieldtype="Select"><div class="control-input flex align-center">
			<select class="form-control" ${disabled ? "disabled" : ""}>${options}</select>
			<div class="select-icon">${frappe.utils.icon("chevrons-up-down", "sm")}</div>
		</div></div>`;
	const icon_button = (icon, title, attrs, theme) =>
		frappe.ui.button.html({ variant: "ghost", icon, title, theme, attrs });

	const send_row = () => {
		const reachable = said.groups.flatMap((group) =>
			group.reachable.map((one) => ({ ...one, at: group.said }))
		);
		const options = reachable
			.map((one) => {
				const label = said.groups.length > 1 ? `${one.name} (${one.at})` : `${one.name} · ${one.email}`;
				return `<option value="${esc(one.contact)}">${esc(label)}</option>`;
			})
			.join("");
		const parties =
			said.groups.length > 1
				? select(
						"ps-party",
						said.groups.map((group) => `<option value="${esc(group.party)}">${esc(group.said)}</option>`).join("")
				  )
				: "";
		const can = said.answers ? __("The recipient can reply through this link once.") : "";
		return `<div class="ps-send">
				${select("ps-to", `${options}<option value="">${__("Someone else…")}</option>`)}
				${frappe.ui.button.html({ variant: "solid", icon: "send", label: __("Send Link"), attrs: { "data-send": 1 } })}
				${icon_button("copy", __("Copy a link without sending it"), { "data-copy-new": 1 })}
			</div>
			<div class="ps-other">
				<input class="form-control ps-email" type="email" placeholder="${__("Email address")}">
				${parties}
			</div>
			<p class="ps-note">${esc(__("No account needed. It opens until {0}.", [said.until]))} ${can}</p>`;
	};

	const record = first.kind === "record";
	const people = () => {
		const many = said.groups.length > 1;
		const rows = said.groups
			.map((group) => {
				const head = many ? `<div class="ps-party-head">${esc(group.said)}</div>` : "";
				if (!group.people.length) {
					return `${head}<p class="ps-note">${esc(__("{0} has no contacts yet.", [group.said]))}</p>`;
				}
				return (
					head +
					group.people
						.map((one) => {
							const sees =
								record && one.sees !== null
									? select(
											"ps-sees",
											`<option value="1" ${one.sees ? "selected" : ""}>${__("Can see")}</option>
											<option value="0" ${one.sees ? "" : "selected"}>${__("Hidden")}</option>`,
											!said.may
									  )
									: "";
							let act = "";
							if (group.may_invite && !one.status && one.email) {
								act = frappe.ui.button.html({ variant: "outline", label: __("Invite"), attrs: { "data-person": "invite_contact" } });
							} else if (group.may_invite && one.status === "revoked") {
								act = frappe.ui.button.html({ variant: "outline", label: __("Restore"), attrs: { "data-person": "restore" } });
							} else if (group.may_invite && ["invited", "active"].includes(one.status)) {
								act = icon_button("ellipsis", __("More"), { "data-more": one.status });
							}
							return `<div class="ps-row" data-contact="${esc(one.contact)}" data-name="${esc(one.name)}">
								${frappe.get_avatar("avatar-medium", one.name)}
								<span class="ps-who"><span class="ps-name">${esc(one.name)}</span><span class="ps-line">${esc(portal_person_line(one))}</span></span>
								${sees}<span class="ps-actions">${act}</span>
							</div>`;
						})
						.join("")
				);
			})
			.join("");
		return `<div data-tour="portal-people">${record ? `<div class="ps-head">${__("People")}</div>` : ""}${rows}</div>`;
	};

	const links = () => {
		const live = said.links.filter((one) => ["open", "answered"].includes(one.state));
		if (!live.length) return "";
		const rows = live
			.map((one) => {
				const buttons = [
					icon_button("copy", __("Copy"), { "data-verb": "copy" }),
					said.may && one.state === "open" ? icon_button("mail", __("Email Again"), { "data-verb": "mail" }) : "",
					said.may && one.state === "open" ? icon_button("refresh-cw", __("Rotate"), { "data-verb": "rotate" }) : "",
					said.may ? icon_button("x", __("Revoke"), { "data-verb": "revoke" }, "red") : "",
				].join("");
				return `<div class="ps-row" data-link="${esc(one.name)}" data-url="${esc(one.url)}">
					<span class="ps-icon">${frappe.utils.icon("link", "sm")}</span>
					<span class="ps-who"><span class="ps-name">${esc(one.who)}</span><span class="ps-line">${esc(portal_link_line(one))}</span></span>
					<span class="ps-actions">${buttons}</span>
				</div>`;
			})
			.join("");
		return `<div class="ps-head">${__("Links")}</div>${rows}`;
	};

	const draw = () => {
		$body.html(`<div class="ps">${record && said.may && said.groups.length ? send_row() : ""}${people()}${record ? links() : ""}</div>`);
		const person = async (verb, contact) => {
			await frappe.xcall(portal_invite(verb), { contact });
			frappe.show_alert({
				message: { invite_contact: __("Invitation sent"), invite_again: __("Invitation sent"), revoke: __("Access revoked"), restore: __("Access restored") }[verb],
				indicator: "green",
			});
			said = { ...(await frappe.xcall(portal_share("access"), { doctype, name })), links: said.links };
			draw();
		};
		$body.find("[data-person]").on("click", (event) => {
			person(event.currentTarget.dataset.person, $(event.currentTarget).closest(".ps-row").attr("data-contact"));
		});
		$body.find("[data-more]").each((_, el) => {
			const $row = $(el).closest(".ps-row");
			const contact = $row.attr("data-contact");
			new frappe.ui.Dropdown({
				trigger: el,
				align: "end",
				options: [
					el.dataset.more === "invited" && { label: __("Invite Again"), icon: "send", onclick: () => person("invite_again", contact) },
					{
						label: __("Revoke Access"),
						icon: "x",
						theme: "red",
						onclick: () =>
							frappe.confirm(__("Turn off {0}'s portal access? They're signed out at once.", [$row.attr("data-name")]), () => person("revoke", contact)),
					},
				].filter(Boolean),
			});
		});
		const $to = $body.find(".ps-to select");
		const someone = () => $body.find(".ps-other").toggle(!$to.val());
		$to.on("change", someone);
		someone();
		const make = async (send) => {
			const contact = $to.val();
			const made = await frappe.xcall(portal_share("make_link"), {
				doctype,
				name,
				contact: contact || null,
				email: contact ? null : $body.find(".ps-email").val(),
				party: contact ? null : $body.find(".ps-party select").val() || null,
				send: send ? 1 : 0,
			});
			said.links = made.links;
			if (send) frappe.show_alert({ message: __("Link sent"), indicator: "green" });
			else frappe.utils.copy_to_clipboard(made.url);
			draw();
		};
		$body.find("[data-send]").on("click", () => make(true));
		$body.find("[data-copy-new]").on("click", () => make(false));
		$body.find(".ps-sees select").on("change", async () => {
			const hidden = $body
				.find(".ps-sees select")
				.toArray()
				.filter((el) => el.value === "0")
				.map((el) => $(el).closest(".ps-row").attr("data-contact"));
			said = await frappe.xcall(portal_share("set_access"), { doctype, name, hidden });
			draw();
		});
		$body.find("[data-verb]").on("click", async (event) => {
			const $row = $(event.currentTarget).closest(".ps-row");
			const link = $row.attr("data-link");
			const verb = event.currentTarget.dataset.verb;
			if (verb === "copy") return frappe.utils.copy_to_clipboard($row.attr("data-url"));
			if (verb === "mail") {
				await frappe.xcall(portal_share("mail_link"), { name: link });
				return frappe.show_alert({ message: __("Link sent"), indicator: "green" });
			}
			if (verb === "revoke") {
				return frappe.confirm(__("Disable this link? Anyone who has it will no longer be able to open it."), async () => {
					said.links = await frappe.xcall(portal_share("revoke_link"), { name: link });
					draw();
				});
			}
			frappe.confirm(__("Make a new link in its place? The old one stops opening."), async () => {
				const made = await frappe.xcall(portal_share("rotate_link"), { name: link, send: 0 });
				frappe.utils.copy_to_clipboard(made.url);
				said.links = made.links;
				draw();
			});
		});
	};
	draw();
	dialog.show();
	// The dialog has no foot to start its tour from, so it starts here the
	// first time it opens (one_portal/tour.py).
	if ((frappe.boot.one_tours_unseen || []).includes("OnePortal:dialog")) {
		setTimeout(async () => {
			const tour = await onedesk.tour.here("OnePortal");
			if (tour && dialog.display) onedesk.tour.run("OnePortal", tour);
		}, 600);
	}
}

PORTAL_KINDS.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			if (frm.doc.docstatus !== 1 || !onedesk.portal.on()) return;
			if (doctype === "Quotation" && frm.doc.quotation_to !== "Customer") return;
			onedesk.portal.button(frm, () => onedesk.portal.open(doctype, frm.doc.name));
		},
	});
});

["Customer", "Supplier"].forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			if (frm.is_new() || !onedesk.portal.on()) return;
			onedesk.portal.button(frm, () => onedesk.portal.open(doctype, frm.doc.name));
		},
	});
});

// OnePortal's settings (docs/READY.md, mechanism 5): what every module's
// finds, its roles and its notifications (module_settings.centers).
onedesk.portal.settings = ({ at = null } = {}) => {
	const dialog = onedesk.module_settings.open({ module: "OnePortal", tabs: [], default_tab: at });
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OnePortal = onedesk.portal.settings;

// Its foot: Settings, Help and the version at the foot of its rail. Its
// screens are frappe's lists, so the window draws it (module_foot).
$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.window.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== "OnePortal") return;
		win.module_foot({ module: "OnePortal", settings: () => onedesk.portal.settings() });
		onedesk.window.nav.place();
	}, 0)
);
