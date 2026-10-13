// On a phone a page's head is two bars (docs/STANDARD.md, The head). The
// first is for the kind of record: the panel's button, the place, the page's
// buttons and search. The second is for the record: its name, its status and
// what narrows it, or a list's view switch, and is there only when it has
// something. Frappe keeps all of it in one row, where the names are cut to
// make room for the buttons. Laid out in desk.css; here the buttons and the
// status are moved, the head says whether its second bar has anything, and
// its height is told to frappe's
// sticky parts (the form's tabs, a report's grid) through
// --page-head-height, as frappe's own CSS reads it. A record's status, which
// frappe shrinks to a dot and then hides on a phone, is a pill with its word
// beside the record's name.
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
	// The record's status: beside its name, in the title on a wider screen
	// and in the second bar on a phone, where frappe has no room for it.
	const place_pill = (head, phone) => {
		const pill = head.querySelector(".page-indicator-pill");
		const actions = head.querySelector(".page-actions");
		const title = head.querySelector(".title-area");
		if (!pill || !actions || !title) return;
		if (phone && pill.parentElement !== actions) actions.prepend(pill);
		else if (!phone && pill.parentElement !== title) title.append(pill);
	};
	// The page's buttons (··· and the main one): in the first bar on a
	// phone, before search, so the second bar is the record's alone.
	const place_buttons = (head, phone) => {
		const buttons = head.querySelector(".standard-actions");
		const actions = head.querySelector(".page-actions");
		const search = head.querySelector(".standard-items-section > .search-bar");
		if (!buttons || !actions) return;
		if (phone && search && buttons.nextElementSibling !== search) search.before(buttons);
		else if (!phone && buttons.parentElement !== actions) actions.append(buttons);
	};
	const sync = () => {
		const head = current();
		if (head) place_pill(head, PHONE.matches);
		if (head) place_buttons(head, PHONE.matches);
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
