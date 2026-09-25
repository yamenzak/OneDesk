// The agreements a workspace runs under, asked for once when the desk starts
// (one_legal/gate.py). A dialog that cannot be closed, because carrying on is
// carrying on under the agreement. The documents themselves open on the
// Agreements page in a new tab, which is never behind this dialog.

frappe.provide("onedesk.legal");

// The desktop at /desk has no route, and frappe.get_route() answers null there.
onedesk.legal.here = () => (frappe.get_route() || [])[0] || "";

onedesk.legal.check = async function () {
	const user = frappe.session.user;
	if (!user || user === "Guest" || user === "Administrator") return;
	if (onedesk.legal.here() === "legal") return;
	let said;
	try {
		said = await frappe.xcall("onedesk.one_legal.gate.outstanding", {}, "GET");
	} catch (e) {
		return;
	}
	if (!said.ok) onedesk.legal.ask(said);
};

onedesk.legal.ask = function (said) {
	if (onedesk.legal.dialog) onedesk.legal.dialog.hide();
	const esc = frappe.utils.escape_html;
	const mine = said.blocking || [];
	const keys = [...new Set(mine.map((one) => one.document))];
	const listed = keys
		.map((key) => {
			const rows = mine.filter((one) => one.document === key);
			const first = rows[0];
			const whose = rows.map((one) => (one.party === "Workspace" ? __("For your organisation") : __("For you")));
			return `<li class="ol-ask-row">
				<div class="ol-ask-title">
					<a href="/app/legal?document=${encodeURIComponent(key)}" target="_blank" rel="noopener">${esc(__(first.title))}</a>
					${whose.map((label) => frappe.ui.badge.html({ label, theme: "gray" })).join(" ")}
					${rows.some((one) => one.previously) ? frappe.ui.badge.html({ label: __("Updated"), theme: "orange" }) : ""}
				</div>
				<div class="ol-ask-summary">${esc(__(first.summary))}</div>
			</li>`;
		})
		.join("");
	const waiting = (said.waiting || []).map((one) => esc(__(one.title))).join(", ");

	const fields = [];
	if (keys.length) {
		fields.push({
			fieldtype: "HTML",
			fieldname: "list",
			options: `<p class="ol-ask-intro">${esc(
				said.may_bind
					? __("As an administrator of this workspace, you agree to some of these for your organisation, and to the rest for yourself.")
					: __("These are about you, so only you can agree to them.")
			)}</p><ul class="ol-ask">${listed}</ul>`,
		});
		fields.push({ fieldtype: "Check", fieldname: "agreed", label: __("I have read these and I agree to them") });
	}
	if (waiting) {
		fields.push({
			fieldtype: "HTML",
			fieldname: "waiting",
			options: `<p class="ol-ask-intro">${esc(
				__("Your workspace's administrator has not yet agreed to {0} for your organisation. One opens once they have.", [waiting])
			)}</p>`,
		});
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Before you carry on"),
		static: true,
		fields,
		primary_action_label: keys.length ? __("Agree") : __("Check Again"),
		primary_action: async (values) => {
			if (keys.length && !values.agreed) {
				frappe.show_alert({ message: __("Tick the box to agree."), indicator: "orange" });
				return;
			}
			const next = keys.length
				? await frappe.xcall("onedesk.one_legal.gate.accept", { documents: keys })
				: await frappe.xcall("onedesk.one_legal.gate.outstanding", {}, "GET");
			if (next.ok) {
				dialog.hide();
				onedesk.legal.dialog = null;
				frappe.show_alert({ message: __("Thank you."), indicator: "green" });
				$(document).trigger("legal-agreed");
				return;
			}
			onedesk.legal.ask(next);
		},
		secondary_action_label: __("Sign Out"),
		secondary_action: () => frappe.app.logout(),
	});
	onedesk.legal.dialog = dialog;
	dialog.show();
};

$(document).on("app_ready", () => onedesk.legal.check());

// A tab opened on the Agreements page skips the dialog so the text can be read.
// Leaving that page asks again.
frappe.router.on("change", () => {
	if (onedesk.legal.here() !== "legal" && !onedesk.legal.dialog && onedesk.legal.skipped) onedesk.legal.check();
	onedesk.legal.skipped = onedesk.legal.here() === "legal";
});
