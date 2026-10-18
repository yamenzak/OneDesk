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
	const place_pill = (head, phone) => {
		const pill = head.querySelector(".page-indicator-pill");
		const actions = head.querySelector(".page-actions");
		const title = head.querySelector(".title-area");
		if (!pill || !actions || !title) return;
		if (phone && pill.parentElement !== actions) actions.prepend(pill);
		else if (!phone && pill.parentElement !== title) title.append(pill);
	};
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
