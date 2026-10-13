// On a phone a page's head is two rows (docs/STANDARD.md, The head). The
// first is the panel's button, the breadcrumb across the width and search;
// the second is the page's buttons, and is there only when the page has
// some. Frappe keeps both in one row, where the name of the place and the
// record is cut to make room for the buttons. Laid out in desk.css; here the
// head says whether it has buttons, and its height is told to frappe's
// sticky parts (the form's tabs, a report's grid) through
// --page-head-height, as frappe's own CSS reads it. A record's status, which
// frappe shrinks to a dot and then hides on a phone, is a pill with its word
// at the start of the second row.
{
	const Page = frappe.ui.Page;
	if (Page && !Page.prototype.__one_phone_pill) {
		Page.prototype.__one_phone_pill = true;
		const set = Page.prototype.set_indicator;
		Page.prototype.set_indicator = function (label, color) {
			const said = set.call(this, label, color);
			if (frappe.is_mobile()) this.indicator.empty().append($("<span>").text(label));
			return said;
		};
	}

	const PHONE = window.matchMedia("(max-width: 767.98px)");
	const root = document.documentElement;
	const current = () => {
		const page = frappe.container?.page;
		return page ? page.querySelector(".page-head") : null;
	};
	// The record's status: beside its name on a wider screen, first in the
	// second row on a phone, where frappe has no room for it.
	const place_pill = (head, phone) => {
		const pill = head.querySelector(".page-indicator-pill");
		const actions = head.querySelector(".page-actions");
		const title = head.querySelector(".title-area");
		if (!pill || !actions || !title) return;
		if (phone && pill.parentElement !== actions) actions.prepend(pill);
		else if (!phone && pill.parentElement !== title) title.append(pill);
	};
	const sync = () => {
		const head = current();
		if (head) place_pill(head, PHONE.matches);
		if (!PHONE.matches || !head) return void root.style.removeProperty("--page-head-height");
		const actions = head.querySelector(".page-actions");
		const any =
			!!actions &&
			[...actions.querySelectorAll("button, a, .page-indicator-pill:not(.hide)")].some((el) => el.getClientRects().length);
		head.classList.toggle("one-head-actions", any);
		if (head.offsetHeight) root.style.setProperty("--page-head-height", `${head.offsetHeight}px`);
	};
	const later = frappe.utils.debounce(sync, 30);
	const watching = new MutationObserver(later);
	const watch = () => {
		watching.disconnect();
		const head = current();
		if (head) watching.observe(head, { subtree: true, childList: true, attributes: true, attributeFilter: ["class", "style"] });
		sync();
	};
	$(document).on("page-change", () => setTimeout(watch, 0));
	PHONE.addEventListener("change", sync);
	$(watch);
}
