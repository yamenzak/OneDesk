// The workspace's own account, from inside the workspace.
//
// Everything here is a copy. The account and the addresses belong to the
// administrator; `one/account.py` asks it, writes down what it said, and the
// screen draws from that — so it keeps drawing when the administrator is slow
// and says when the answer went stale.
//
// Nothing is typed. Adding an address is a dialog rather than a row, because
// the address has to be checked against DNS before it is claimed, and a grid
// row cannot ask a question.
frappe.ui.form.on("Workspace Account", {
	refresh(frm) {
		onedesk.account.draw(frm);
		if (!frappe.user.has_role("Workspace Administrator")) return;

		frm.add_custom_button(__("Add Domain"), () => onedesk.account.add(frm), __("Domains"));
		frm.add_custom_button(__("Set Primary"), () => onedesk.account.pick(frm, "primary"), __("Domains"));
		frm.add_custom_button(__("Remove"), () => onedesk.account.pick(frm, "drop"), __("Domains"));
		frm.add_custom_button(__("Refresh"), () =>
			frappe
				.xcall("onedesk.one.account.domains_refresh")
				.then(() => frm.reload_doc())
				.catch(() => frm.reload_doc()),
		);
		frm.add_custom_button(__("Buy credits"), () => onedesk.account.buy(frm)).addClass(
			frm.doc.credits_balance > 0 ? "" : "btn-primary",
		);
	},
});

frappe.provide("onedesk.account");

onedesk.account.SAYS = {
	Requested: ["orange", __("Being set up")],
	Provisioning: ["blue", __("Being set up")],
	Live: ["green", __("Active")],
	Overdue: ["orange", __("Payment overdue")],
	Suspended: ["red", __("Suspended")],
	Archived: ["grey", __("Archived")],
};

onedesk.account.draw = (frm) => {
	const [colour, word] = onedesk.account.SAYS[frm.doc.status] || ["grey", frm.doc.status || ""];
	if (word) frm.page.set_indicator(word, colour);

	// One headline, and the money one wins. A workspace about to be suspended
	// has to be told how long it has; that it could not reach its account is
	// worth saying too, but not instead.
	const said = [];
	let colourOf = "blue";
	if (frm.doc.owing && frm.doc.next_status) {
		const left = frm.doc.days_left;
		said.push(
			left === 0
				? __("Payment overdue. This workspace is suspended tonight.")
				: __("Payment overdue. This workspace is suspended in {0} days.", [left]),
		);
		colourOf = left !== null && left <= 2 ? "red" : "orange";
	} else if (frm.doc.last_error) {
		said.push(__("Could not reach your account. Showing what was last known."));
		colourOf = "orange";
	}
	frm.dashboard.clear_headline();
	if (said.length) frm.dashboard.set_headline(said.join(" "), colourOf);

	onedesk.account.credits(frm);

	const limit = Number(frm.doc.storage_limit || 0);
	const used = Number(frm.doc.storage_bytes || 0);
	if (limit) {
		frm.dashboard.add_progress(
			__("Storage"),
			[
				{
					width: `${Math.min(100, (used / limit) * 100)}%`,
					progress_class: used > limit ? "progress-bar-danger" : "progress-bar-success",
					title: onedesk.tenant.size(used),
				},
			],
			used > limit
				? __("{0} over the {1} this plan allows.", [
						onedesk.tenant.size(used - limit),
						onedesk.tenant.size(limit),
					])
				: __("{0} of {1} used.", [onedesk.tenant.size(used), onedesk.tenant.size(limit)]),
		);
	}
};

// Credits, in words. The three numbers underneath are what a bill is settled
// from and are the wrong things to read, so the sentence goes above them.
//
// What is held is said separately from what is left, because a workspace whose
// balance looks fine and whose calls are being refused is looking at the same
// number twice.
onedesk.account.credits = (frm) => {
	const field = frm.get_field("credits_said");
	if (!field) return;
	const balance = Number(frm.doc.credits_balance || 0);
	const held = Number(frm.doc.credits_held || 0);
	const expiring = Number(frm.doc.credits_expiring || 0);

	const said = [];
	said.push(
		balance > 0
			? __("{0} credits.", [onedesk.account.round(balance)])
			: balance < 0
				? __("{0} credits over. Buy some to keep using the AI.", [
						onedesk.account.round(-balance),
					])
				: __("No credits. Buy some to use the AI."),
	);
	if (held > 0) said.push(__("{0} of them are promised to calls in flight.", [onedesk.account.round(held)]));
	if (expiring > 0 && frm.doc.credits_expires_on) {
		said.push(
			__("{0} expire on {1}.", [
				onedesk.account.round(expiring),
				frappe.datetime.str_to_user(frm.doc.credits_expires_on),
			]),
		);
	}
	field.$wrapper.html(
		`<p class="${balance > 0 ? "text-muted" : "text-danger"}">${said.join(" ")}</p>`,
	);
};

// Six places is what the ledger keeps and three is what anybody reads. The
// stored number is not rounded; only this sentence is.
onedesk.account.round = (n) => Number(n.toFixed(3));

// A price list rather than a box to type a number in. Which pack is a decision
// somebody made in the account, and a calculator here would be a second place
// where credits per dollar is decided.
onedesk.account.buy = (frm) => {
	frappe.xcall("onedesk.one.account.credit_packs").then((packs) => {
		if (!packs.length) {
			frappe.msgprint(__("No credit pack is on sale at the moment."));
			return;
		}
		const box = new frappe.ui.Dialog({
			title: __("Buy credits"),
			fields: [
				{
					fieldname: "pack",
					fieldtype: "Select",
					label: __("Pack"),
					reqd: 1,
					options: packs.map((one) => one.name),
					default: packs[0].name,
				},
				{ fieldname: "said", fieldtype: "HTML" },
			],
			primary_action_label: __("Go to payment"),
			primary_action({ pack }) {
				frappe.xcall("onedesk.one.account.buy_credits", { pack }).then((where) => {
					box.hide();
					window.location.href = where.pay_at;
				});
			},
		});
		const draw = () => {
			const one = packs.find((p) => p.name === box.get_value("pack")) || packs[0];
			box.fields_dict.said.$wrapper.html(
				`<p><b>${__("{0} credits", [one.credits])}</b> ` +
					`${__("for")} ${format_currency(one.amount, one.currency)}</p>` +
					(one.description
						? `<p class="text-muted">${frappe.utils.escape_html(one.description)}</p>`
						: ""),
			);
		};
		box.fields_dict.pack.df.onchange = draw;
		box.show();
		draw();
	});
};

// Adding an address, in the order somebody actually does it: type the name,
// point the DNS at us, check that it took, then claim it. The check is its own
// button because it costs nothing and undoes nothing.
onedesk.account.add = (frm) => {
	const box = new frappe.ui.Dialog({
		title: __("Add a domain"),
		fields: [
			{
				fieldname: "domain",
				fieldtype: "Data",
				label: __("Domain"),
				reqd: 1,
				description: __("For example hr.example.com. Do not include https://"),
			},
			{
				fieldname: "how",
				fieldtype: "HTML",
				options: `<div class="text-muted small">${__(
					"Point a CNAME for this name at {0}, without a proxy, then check it.",
					[frappe.utils.escape_html(frm.doc.domain || "")],
				)}</div>`,
			},
			{ fieldname: "said", fieldtype: "HTML" },
		],
		primary_action_label: __("Add"),
		primary_action: ({ domain }) =>
			frappe
				.xcall("onedesk.one.account.domain_add", { domain })
				.then(() => {
					box.hide();
					frm.reload_doc();
				}),
		secondary_action_label: __("Check DNS"),
		secondary_action: () => {
			const domain = box.get_value("domain");
			if (!domain) return;
			box.set_df_property("said", "options", `<div class="text-muted">${__("Checking…")}</div>`);
			frappe
				.xcall("onedesk.one.account.domain_check", { domain })
				.then((said) =>
					box.set_df_property(
						"said",
						"options",
						said && said.valid
							? `<div class="text-success">${__("The DNS is pointing here.")}</div>`
							: `<div class="text-muted">${__("Not pointing here yet.")}</div>`,
					),
				)
				// A refusal from Frappe Cloud is shown by frappe itself and says
				// what to fix, including the one about turning a proxy off.
				.catch(() => box.set_df_property("said", "options", ""));
		},
	});
	box.show();
};

// Choosing which address to act on. A grid row cannot carry a button, and the
// two verbs here both need a confirmation anyway.
onedesk.account.pick = (frm, verb) => {
	const rows = (frm.doc.domains || []).filter((one) =>
		verb === "primary" ? !one.primary && one.status === "Active" : !one.given,
	);
	if (!rows.length) {
		frappe.msgprint(
			verb === "primary"
				? __("No other address is working yet.")
				: __("There is nothing to remove."),
		);
		return;
	}

	const box = new frappe.ui.Dialog({
		title: verb === "primary" ? __("Set the main address") : __("Remove a domain"),
		fields: [
			{
				fieldname: "domain",
				fieldtype: "Select",
				label: __("Domain"),
				reqd: 1,
				options: rows.map((one) => one.domain).join("\n"),
			},
		],
		primary_action_label: verb === "primary" ? __("Set Primary") : __("Remove"),
		primary_action: ({ domain }) => {
			box.hide();
			const method =
				verb === "primary"
					? "onedesk.one.account.domain_primary"
					: "onedesk.one.account.domain_drop";
			frappe.confirm(
				verb === "primary"
					? __("Use {0} as this workspace's main address?", [domain])
					: __("Remove {0}? The workspace will stop answering there.", [domain]),
				() => frappe.xcall(method, { domain }).then(() => frm.reload_doc()),
			);
		},
	});
	box.show();
};
