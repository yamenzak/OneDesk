frappe.provide("onedesk.window");

// Going to another screen keeps the one on screen until the next has drawn,
// then fades across: a screen opened for the first time otherwise shows an
// empty window and then Loading before it draws.
onedesk.window.HOLD = 900;

onedesk.window.drawn = (before, was) =>
	new Promise((done) => {
		const until = Date.now() + onedesk.window.HOLD;
		const look = () => {
			const page = frappe.container?.page;
			const island = page && $(page).find(".one-island").get(0);
			const drawn = island?.querySelector(".frappe-island")?.shadowRoot;
			const shown = page && (page !== before || page._route !== was);
			const waiting = !shown || (island && (!drawn?.childElementCount || drawn.querySelector(".one-loading")));
			if (!waiting || Date.now() > until) return done();
			setTimeout(look, 40);
		};
		setTimeout(look, 40);
	});

onedesk.window.screen = (path) => (path || "").split("?")[0].split("/").slice(0, 2).join("/");

$(() => {
	const route = frappe.router?.route;
	if (!route || !document.startViewTransition) return;
	frappe.router.route = function (...args) {
		const from = onedesk.window.screen(this.current_sub_path);
		const to = onedesk.window.screen(this.get_sub_path());
		if (!frappe.app || from === to || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
			return route.apply(this, args);
		}
		onedesk.window.switching?.skipTransition();
		let ran;
		const switching = document.startViewTransition(() => {
			const before = frappe.container?.page;
			const was = before?._route;
			ran = route.apply(this, args);
			return Promise.resolve(ran).then(() => onedesk.window.drawn(before, was));
		});
		onedesk.window.switching = switching;
		switching.finished.finally(() => onedesk.window.switching === switching && (onedesk.window.switching = null));
		return switching.updateCallbackDone.then(() => ran, () => ran);
	};
});
