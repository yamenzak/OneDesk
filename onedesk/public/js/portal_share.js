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

const portal_share = (name) => `onedesk.one.portal_share.${name}`;

function portal_link_line(one) {
	if (one.state === "answered") return __("Answered by {0}, {1}", [one.used_by, one.used_on]);
	const opened =
		one.opened === 0 ? __("Not opened yet") : one.opened === 1 ? __("Opened once") : __("Opened {0} times", [one.opened]);
	return `${opened} · ${__("until {0}", [one.expires])}`;
}

function portal_dialog(frm, first) {
	const doctype = frm.doc.doctype;
	const name = frm.doc.name;
	const esc = frappe.utils.escape_html;
	const dialog = new frappe.ui.Dialog({
		title: __("{0} on the Portal", [name]),
		fields: [{ fieldtype: "HTML", fieldname: "body" }],
		primary_action_label: __("Done", null, "Close a dialog"),
		primary_action: () => dialog.hide(),
	});
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
		const can = said.answers ? __("They can answer through it once.") : "";
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

	const people = () => {
		const many = said.groups.length > 1;
		const rows = said.groups
			.map((group) => {
				const head = many ? `<div class="ps-party-head">${esc(group.said)}</div>` : "";
				if (!group.people.length) {
					return `${head}<p class="ps-note">${esc(__("Nobody at {0} signs in to the portal yet.", [group.said]))}</p>`;
				}
				return (
					head +
					group.people
						.map(
							(one) => `<div class="ps-row" data-contact="${esc(one.contact)}">
							${frappe.get_avatar("avatar-medium", one.name)}
							<span class="ps-who"><span class="ps-name">${esc(one.name)}</span><span class="ps-line">${esc(one.email || "")}</span></span>
							${select(
								"ps-sees",
								`<option value="1" ${one.sees ? "selected" : ""}>${__("Can see")}</option>
								<option value="0" ${one.sees ? "" : "selected"}>${__("Hidden")}</option>`,
								!said.may
							)}
						</div>`
						)
						.join("")
				);
			})
			.join("");
		return `<div class="ps-head">${__("People on the portal")}</div>${rows}`;
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
		$body.html(`<div class="ps">${said.may ? send_row() : ""}${people()}${links()}</div>`);
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
				return frappe.confirm(__("Stop this link opening? Whoever has it can't use it any more."), async () => {
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
}

PORTAL_KINDS.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			if (frm.doc.docstatus !== 1) return;
			if (doctype === "Quotation" && frm.doc.quotation_to !== "Customer") return;
			frm.add_custom_button(__("Portal"), async () => {
				portal_dialog(frm, await frappe.xcall(portal_share("access"), { doctype, name: frm.doc.name }));
			});
		},
	});
});
