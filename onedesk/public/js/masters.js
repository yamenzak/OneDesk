// Masters (one/masters.py): each kind is frappe's own list and form. What is
// ours is the tree beside any of them, in the nav pane under the rail's
// Masters, of every kind the reader may open, grouped by the app that uses it,
// with how many values each has; a group folds, and stays folded.
frappe.provide("onedesk.masters");

onedesk.masters.covers = (doctype) => (frappe.boot.one_masters || []).includes(doctype);

onedesk.masters.folded = () => onedesk.masters._folded || [];

onedesk.masters.draw = async ($slot, doctype) => {
	if (!onedesk.masters._folded) onedesk.masters._folded = ((await frappe.model.user_settings.get("Masters")) || {}).closed || [];
	const kinds = await frappe.xcall("onedesk.one.masters.kinds");
	const esc = frappe.utils.escape_html;
	const groups = [...new Set(kinds.map((one) => one.group))];
	const here = kinds.find((one) => one.doctype === doctype);
	const html = groups
		.map((group) => {
			const mine = kinds.filter((one) => one.group === group);
			const open = !onedesk.masters.folded().includes(group) || (here && here.group === group);
			const mark = mine[0].mark ? frappe.utils.icon(mine[0].mark, "sm") : frappe.utils.icon("folder", "sm");
			const head = `<div class="standard-sidebar-item one-masters-group" data-group="${esc(group)}" style="--depth:0">
				<a class="item-anchor" href="#" aria-expanded="${open}"><span class="one-window-twisty">${frappe.utils.icon(open ? "chevron-down" : "chevron-right", "xs")}</span><span class="sidebar-item-icon">${mark}</span><span class="sidebar-item-label">${esc(group === "Shared" ? __("Shared") : group)}</span></a>
			</div>`;
			const rows = open
				? mine
						.map(
							(one) => `<div class="standard-sidebar-item${one.doctype === doctype ? " active-sidebar" : ""}" style="--depth:1">
								<a class="item-anchor" href="/desk/${frappe.router.slug(one.doctype)}"><span class="one-window-twisty"></span><span class="sidebar-item-label">${esc(one.label)}</span><span class="one-window-count">${cint(one.count)}</span></a>
							</div>`
						)
						.join("")
				: "";
			return head + rows;
		})
		.join("");
	$slot.attr("aria-label", __("Masters")).html(html);
	$slot.off(".masters").on("click.masters", ".one-masters-group > .item-anchor", (e) => {
		e.preventDefault();
		const group = $(e.currentTarget).parent().attr("data-group");
		const folded = onedesk.masters.folded();
		onedesk.masters._folded = folded.includes(group) ? folded.filter((one) => one !== group) : [...folded, group];
		frappe.model.user_settings.save("Masters", "closed", onedesk.masters._folded);
		onedesk.masters.draw($slot, doctype);
	});
	frappe.model.user_settings.save("Masters", "last", doctype);
};

onedesk.window.trees.push({ covers: onedesk.masters.covers, draw: onedesk.masters.draw });
