// The desk an island is mounted in (docs/ISLANDS.md). An island runs in desk's
// own window, so what desk already does is asked of desk and never redone:
// its words and formats, its calls (CSRF, errors as desk shows them), its
// routes, its realtime and its dialogs.

const frappe = () => window.frappe;

/** Desk's translation, as `__` everywhere else in OneDesk. */
export function __(text, args, context) {
	if (window.__) return window.__(text, args, context);
	return String(text).replace(/\{(\d+)\}/g, (_, i) => (args || [])[Number(i)] ?? "");
}

/** A whitelisted method, through desk's own `frappe.xcall`. */
export const call = (method, args = {}) => frappe().xcall(method, args);

/** Money as desk formats it, whole units, kept left-to-right in Arabic. */
export function money(value, currency) {
	const said = window.format_currency(value || 0, currency, 0);
	return window.onedesk?.shell?.ltr ? window.onedesk.shell.ltr(said) : said;
}

/** A date as the reader's settings write it. */
export const date = (value) => (value ? frappe().datetime.str_to_user(value) : "");

/** Hours, to one decimal where there is one. */
export const hours = (value) =>
	__("{0} h", [window.format_number(value || 0, null, Number(value) % 1 ? 1 : 0)]);

/** Go somewhere in desk. */
export const go = (route) => frappe().set_route(route);

/** What the reader may do to a doctype: `can("create", "Sales Invoice")`. */
export const can = (action, doctype) => Boolean(frappe().model[`can_${action}`]?.(doctype));

/**
 * Follow a record as a desk form does: listen on its room and hear when it is
 * saved. Returns the way to stop.
 */
export function follow(doctype, name, changed) {
	const realtime = frappe().realtime;
	const heard = (data) => data.doctype === doctype && data.name === name && changed(data);
	realtime.doc_subscribe(doctype, name);
	realtime.on("doc_update", heard);
	return () => {
		realtime.off("doc_update", heard);
		realtime.doc_unsubscribe(doctype, name);
	};
}

/** Listen for one of OneDesk's own realtime events. Returns the way to stop. */
export function listen(event, heard) {
	frappe().realtime.on(event, heard);
	return () => frappe().realtime.off(event, heard);
}

/** A new record, opened in desk's form as frappe.new_doc opens one. */
export const newDoc = (doctype, values) => frappe().new_doc(doctype, values);

/** OneDesk's own desk-side code: its dialogs and actions (public/js). */
export const onedesk = () => window.onedesk;
