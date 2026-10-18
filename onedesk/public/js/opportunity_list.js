(() => {
	const settings = (frappe.listview_settings["Opportunity"] ||= {});
	settings.formatters = { ...settings.formatters, ...onedesk.next_step.formatters };
	const COLOUR = { Open: "blue", Replied: "orange", Quotation: "purple", Converted: "green", Lost: "gray", Closed: "gray" };
	settings.get_indicator = (doc) => [__(doc.status), COLOUR[doc.status] || "gray", `status,=,${doc.status}`];
	settings.filters = [["status", "in", ["Open", "Quotation", "Replied"]]];

	if (frappe.one_pipeline_worth) return;
	frappe.one_pipeline_worth = true;

	const paint = frappe.utils.debounce(worth, 300);
	new MutationObserver((changes) => {
		const [view, doctype, kind] = frappe.get_route() || [];
		if (view !== "List" || doctype !== "Opportunity" || kind !== "Kanban") return;
		if (changes.some((change) => !change.target.closest?.(".one-stage-worth, .one-place-spot"))) paint();
	}).observe(document.body, { childList: true, subtree: true, characterData: true });

	async function worth() {
		const listview = window.cur_list;
		const board = listview?._kanban;
		if (listview?.view_name !== "Kanban" || listview.doctype !== "Opportunity" || !board) return;
		if (board.field_name !== "sales_stage") return;
		const { currency, stages } = await frappe.xcall("onedesk.one_crm.board.worth", {
			filters: board.get_effective_filters(),
		});
		const money = (value) => `<bdi>${format_currency(value, currency, 0)}</bdi>`;
		board.$container.find(".kn-column").each(function () {
			const stage = stages[this.dataset.col] || { value: 0, weighted: 0 };
			const said =
				stage.weighted && stage.weighted !== stage.value
					? __("{0} · {1} weighted", [money(stage.value), money(stage.weighted)])
					: money(stage.value);
			let $worth = $(this).find(".one-stage-worth");
			if (!$worth.length) {
				$worth = $('<div class="one-stage-worth"></div>').insertAfter(
					$(this).find(".kn-column-header")
				);
			}
			if ($worth.html() !== said) $worth.html(said);
		});
		extended(board, currency, stages);
	}

	let told = null;
	function extended(board, currency, stages) {
		if (!onedesk.places || !onedesk.places.listening("onecrm.board")) return;
		const key = JSON.stringify([currency, stages]);
		if (key === told && board.$container.find(".one-place-spot").length) return;
		told = key;
		board.$container.find(".one-place-spot").remove();
		const powers = onedesk.places.spot(($spot) => board.$container.prepend($spot));
		onedesk.places.emit("onecrm.board", { currency, stages }, powers);
	}
})();
