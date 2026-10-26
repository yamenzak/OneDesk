
frappe.provide("onedesk.legal");

// Read from the address too: at app_ready, a tab opened on the page from the
// dialog's own link has no route yet, and was asked again over the page.
onedesk.legal.here = () =>
	(frappe.get_route() || [])[0] || (location.pathname.split("/").includes("legal") ? "legal" : "");

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
					? __("As a workspace administrator, you agree to some of these for your organisation.")
					: __("Only you can agree to these.")
			)}</p><ul class="ol-ask">${listed}</ul>`,
		});
		fields.push({ fieldtype: "Check", fieldname: "agreed", label: __("I agree to these") });
	}
	if (waiting) {
		fields.push({
			fieldtype: "HTML",
			fieldname: "waiting",
			options: `<p class="ol-ask-intro">${esc(
				__("One opens once your workspace administrator agrees to {0}.", [waiting])
			)}</p>`,
		});
	}

	const dialog = new frappe.ui.Dialog({
		title: __("Before You Continue"),
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
				frappe.show_alert({ message: __("Agreed"), indicator: "green" });
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

frappe.router.on("change", () => {
	if (onedesk.legal.here() !== "legal" && !onedesk.legal.dialog && onedesk.legal.skipped) onedesk.legal.check();
	onedesk.legal.skipped = onedesk.legal.here() === "legal";
});
