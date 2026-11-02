// Likes are stars (onedesk/one_interface/AGENTS.md, Stars). A person marks a
// record to find it again, as a browser's star marks a page and a file
// manager's marks a favourite, so it is drawn as one: frappe's like, its
// heart swapped for the star wherever frappe draws it (a list's rows and its
// head, a record, the activity, a board's cards). The data and the toggle are
// frappe's own; only the picture and a small pop when it fills are ours.
frappe.provide("onedesk.interface");

{
	const HEART = 'use[href="#icon-heart"]';
	const starred = (node) => {
		if (!node || node.nodeType !== 1) return;
		if (node.matches(HEART)) node.setAttribute("href", "#icon-star");
		node.querySelectorAll(HEART).forEach((use) => use.setAttribute("href", "#icon-star"));
	};
	onedesk.interface.starred = starred;
	const watch = () => {
		starred(document.body);
		new MutationObserver((changes) => {
			for (const change of changes) change.addedNodes.forEach(starred);
		}).observe(document.body, { childList: true, subtree: true });
	};
	if (document.body) watch();
	else document.addEventListener("DOMContentLoaded", watch);

	// The star pops as it fills; frappe's own toggle does the rest.
	const toggle = frappe.ui.toggle_like;
	if (toggle && !toggle.one_star) {
		frappe.ui.toggle_like = function ($btn, doctype, name, callback) {
			return toggle.call(this, $btn, doctype, name, (...args) => {
				const $icon = $btn.is(".like-icon") ? $btn : $btn.find(".like-icon");
				if ($btn.hasClass("liked") || $btn.closest(".liked").length) {
					$icon.removeClass("one-star-pop");
					void ($icon[0] && $icon[0].getBoundingClientRect());
					$icon.addClass("one-star-pop").one("animationend", () => $icon.removeClass("one-star-pop"));
				}
				if (callback) return callback(...args);
			});
		};
		frappe.ui.toggle_like.one_star = true;
	}
}
