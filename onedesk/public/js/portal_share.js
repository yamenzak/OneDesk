// A submitted record and the portal (one/portal_share.py): Portal opens who
// of its customer's or supplier's portal contacts see it, and its signed
// links for somebody without an account, with Copy, Email Again, Rotate and
// Revoke on each and a new one at the foot.
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

const portal_states = {
	open: [__("Open"), "green"],
	answered: [__("Answered"), "blue"],
	expired: [__("Expired"), "gray"],
	revoked: [__("Revoked"), "gray"],
};

function portal_links_html(links, may) {
	if (!links.length) return `<p class="text-muted">${__("No links yet.")}</p>`;
	const esc = frappe.utils.escape_html;
	return links
		.map((one) => {
			const [state, tone] = portal_states[one.state];
			const said = [
				__("made {0}", [one.made]),
				one.opened === 1
					? __("opened once, {0}", [one.last_opened])
					: one.opened
					? __("opened {0} times, last {1}", [one.opened, one.last_opened])
					: __("not opened yet"),
				one.used_by ? __("answered by {0}", [esc(one.used_by)]) : "",
				one.state === "open" ? __("works until {0}", [one.expires]) : "",
			].filter(Boolean);
			const button = (verb, label, theme) =>
				frappe.ui.button.html({ label, theme, attrs: { "data-verb": verb, "data-link": one.name } });
			const buttons =
				one.state === "open"
					? [
							button("copy", __("Copy")),
							may ? button("mail", __("Email Again")) : "",
							may ? button("rotate", __("Rotate")) : "",
							may ? button("revoke", __("Revoke"), "red") : "",
					  ].join(" ")
					: "";
			return `<div class="portal-link" data-url="${esc(one.url)}">
				<div><b>${esc(one.who)}</b> <span class="indicator-pill ${tone}">${state}</span></div>
				<div class="text-muted small">${esc(one.email)} · ${said.join(" · ")}</div>
				<div class="mt-1">${buttons}</div>
			</div>`;
		})
		.join(`<hr class="my-2">`);
}

function portal_dialog(frm, said) {
	const doctype = frm.doc.doctype;
	const name = frm.doc.name;
	const fields = [{ fieldtype: "Section Break", label: __("Who sees it on the portal") }];
	said.groups.forEach((group, i) => {
		if (!group.people.length) {
			fields.push({
				fieldtype: "HTML",
				fieldname: `none_${i}`,
				options: `<p class="text-muted">${__("No contact of {0} signs in to the portal yet.", [
					frappe.utils.escape_html(group.said),
				])}</p>`,
			});
			return;
		}
		fields.push({
			fieldtype: "MultiCheck",
			fieldname: `sees_${i}`,
			label: group.said,
			columns: 2,
			read_only: !said.may,
			options: group.people.map((one) => ({ label: one.name, value: one.contact, checked: one.sees })),
		});
	});
	fields.push(
		{
			fieldtype: "HTML",
			fieldname: "everyone",
			options: `<p class="text-muted small">${__(
				"Everyone ticked sees it, and so will a contact who signs in later. Untick who shouldn't."
			)}</p>`,
		},
		{ fieldtype: "Section Break", label: __("Links") },
		{
			fieldtype: "HTML",
			fieldname: "about",
			options: `<p class="text-muted small">${__(
				"A link opens this record for one person without an account, until its day. {0}",
				[said.answers ? __("They can answer through it once.") : ""]
			)}</p>`,
		},
		{ fieldtype: "HTML", fieldname: "links" }
	);
	const reachable = said.groups.flatMap((group) =>
		group.reachable.map((one) => ({
			value: one.contact,
			label: said.groups.length > 1 ? `${one.name} (${group.said})` : `${one.name} · ${one.email}`,
		}))
	);
	if (said.may) {
		fields.push(
			{ fieldtype: "Section Break", label: __("New Link") },
			{
				fieldtype: "Select",
				fieldname: "contact",
				label: __("For"),
				options: [...reachable, { value: "", label: __("Someone else…") }],
				default: reachable[0]?.value || "",
			},
			{ fieldtype: "Data", fieldname: "email", label: __("Email"), options: "Email", depends_on: "eval:!doc.contact" },
			{
				fieldtype: "Select",
				fieldname: "party",
				label: __("At"),
				options: said.groups.map((group) => ({ value: group.party, label: group.said })),
				depends_on: `eval:!doc.contact && ${said.groups.length > 1}`,
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Date",
				fieldname: "expires_on",
				label: __("Works until"),
				description:
					doctype === "Quotation"
						? __("Left empty, the quotation's last day or a month from today")
						: __("Left empty, a month from today"),
			},
			{ fieldtype: "Check", fieldname: "send", label: __("Email it to them"), default: 1 },
			{ fieldtype: "Button", fieldname: "make", label: __("Make Link") }
		);
	}
	const dialog = new frappe.ui.Dialog({
		title: __("Portal"),
		size: "large",
		fields,
		primary_action_label: said.may ? __("Save") : __("Close"),
		async primary_action() {
			if (!said.may) return dialog.hide();
			const hidden = said.groups.flatMap((group, i) => {
				if (!group.people.length) return [];
				const ticked = new Set(dialog.get_value(`sees_${i}`) || []);
				return group.people.filter((one) => !ticked.has(one.contact)).map((one) => one.contact);
			});
			await frappe.xcall(portal_share("set_access"), { doctype, name, hidden });
			frappe.show_alert({ message: __("Saved"), indicator: "green" });
			dialog.hide();
			frm.reload_doc();
		},
	});
	const draw = (links) => {
		const wrapper = dialog.fields_dict.links.$wrapper;
		wrapper.html(portal_links_html(links, said.may));
		wrapper.find("button[data-verb]").on("click", async (event) => {
			const { verb, link } = event.currentTarget.dataset;
			if (verb === "copy") {
				frappe.utils.copy_to_clipboard($(event.currentTarget).closest(".portal-link").data("url"));
				return;
			}
			if (verb === "mail") {
				await frappe.xcall(portal_share("mail_link"), { name: link });
				frappe.show_alert({ message: __("Link sent"), indicator: "green" });
				return;
			}
			if (verb === "revoke") {
				frappe.confirm(__("Stop this link opening? Whoever has it can't use it any more."), async () => {
					draw(await frappe.xcall(portal_share("revoke_link"), { name: link }));
				});
				return;
			}
			frappe.confirm(__("Make a new link in its place? The old one stops opening."), async () => {
				const made = await frappe.xcall(portal_share("rotate_link"), { name: link, send: 0 });
				frappe.utils.copy_to_clipboard(made.url);
				draw(made.links);
			});
		});
	};
	draw(said.links);
	if (said.may) {
		frappe.ui.button.dress(dialog.fields_dict.make.$input, { label: __("Make Link"), variant: "solid" });
		dialog.fields_dict.make.input.onclick = async () => {
			const values = dialog.get_values(true);
			const made = await frappe.xcall(portal_share("make_link"), {
				doctype,
				name,
				contact: values.contact || null,
				email: values.contact ? null : values.email,
				party: values.contact ? null : values.party,
				expires_on: values.expires_on ? `${values.expires_on} 23:59:59` : null,
				send: values.send ? 1 : 0,
			});
			if (!values.send) frappe.utils.copy_to_clipboard(made.url);
			else frappe.show_alert({ message: __("Link sent"), indicator: "green" });
			draw(made.links);
		};
	}
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
