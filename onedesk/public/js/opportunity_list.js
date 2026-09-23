// The pipeline board says what each stage is worth, beside the desk's own count.
// The Kanban view does not call a list's onload or refresh, and the count badge
// is redrawn on every load, drag and realtime update, so one observer follows
// the page and paints whenever the Opportunity board is the one on screen.
// See one_crm/board.py.
(() => {
	if (frappe.one_pipeline_worth) return;
	frappe.one_pipeline_worth = true;

	const paint = frappe.utils.debounce(worth, 300);
	new MutationObserver((changes) => {
		const [view, doctype, kind] = frappe.get_route();
		if (view !== "List" || doctype !== "Opportunity" || kind !== "Kanban") return;
		if (changes.some((change) => !change.target.closest?.(".one-stage-worth"))) paint();
	}).observe(document.body, { childList: true, subtree: true, characterData: true });

	async function worth() {
		const listview = window.cur_list;
		if (listview?.view_name !== "Kanban" || listview.doctype !== "Opportunity") return;
		const { currency, stages } = await frappe.xcall("onedesk.one_crm.board.worth", {
			filters: [...listview.get_filters_for_args(), ...(listview.board?.filters_array || [])],
		});
		// Each amount is isolated, or a right-to-left currency sign swaps the two.
		const money = (value) => `<bdi>${format_currency(value, currency, 0)}</bdi>`;
		listview.$result.find(".kanban-column").each(function () {
			const stage = stages[this.dataset.columnValue] || { value: 0, weighted: 0 };
			const said =
				stage.weighted && stage.weighted !== stage.value
					? __("{0} · {1} weighted", [money(stage.value), money(stage.weighted)])
					: money(stage.value);
			let $worth = $(this).find(".one-stage-worth");
			if (!$worth.length) {
				$worth = $('<div class="one-stage-worth"></div>').insertAfter(
					$(this).find(".kanban-column-header")
				);
			}
			if ($worth.html() !== said) $worth.html(said);
		});
	}
})();
