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

/** Money as desk formats it, to the workspace's currency precision, kept left-to-right in Arabic. */
export function money(value, currency) {
	const said = window.format_currency(value || 0, currency);
	return window.onedesk?.shell?.ltr ? window.onedesk.shell.ltr(said) : said;
}

/** A date as the reader's settings write it. */
export const date = (value) => (value ? frappe().datetime.str_to_user(value) : "");

// Desk's date format in the form frappe-ui's DatePicker reads (dd-mm-yyyy → DD-MM-YYYY).
export const dateFormat = () => (frappe().boot.sysdefaults?.date_format || "yyyy-mm-dd").toUpperCase();

/** Hours, to one decimal where there is one. */
export const hours = (value) =>
	__("{0} h", [window.format_number(value || 0, null, Number(value) % 1 ? 1 : 0)]);

/**
 * Colours by name (`--outline-gray-3`) as `el` sees them, for a chart, which
 * draws in values, not variables. An island's own tokens are on its root,
 * not the page's.
 */
export const colors = (el, ...names) => {
	const styles = el ? getComputedStyle(el) : null;
	return names.map((name) => (styles ? styles.getPropertyValue(name).trim() : ""));
};

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

/** Ask for a value or two in desk's own prompt: frappe's fields, its dialog. */
export const prompt = (fields, done, title, label) => frappe().prompt(fields, done, title, label);

/** Ask before doing something that can't be taken back, as desk asks. */
export const confirm = (message, yes) => frappe().confirm(message, yes);
// A list in words, "2 open tasks and 1 open sub-project", as frappe writes it.
export const andList = (items) => frappe().utils.comma_and(items);
export const escape = (text) => frappe().utils.escape_html(text);

/** OneDesk's own desk-side code: its dialogs and actions (public/js). */
export const onedesk = () => window.onedesk;

/** Change one field of a record, as desk does: permissions and validation are the record's. */
export const setValue = (doctype, name, fieldname, value) =>
	call("frappe.client.set_value", { doctype, name, fieldname, value });

/** Make a record. */
export const insert = (doc) => call("frappe.client.insert", { doc });

/** Assign a record to people, or take it off them, through desk's assignments. */
export const assign = (doctype, name, users) =>
	call("frappe.desk.form.assign_to.add", { doctype, name, assign_to: users });
export const unassign = (doctype, name, user) =>
	call("frappe.desk.form.assign_to.remove", { doctype, name, assign_to: user });

/** A comment on a record, as the form's comment box adds one. */
export const comment = (doctype, name, content) =>
	call("frappe.desk.form.utils.add_comment", {
		reference_doctype: doctype,
		reference_name: name,
		content,
		comment_email: frappe().session.user,
		comment_by: frappe().session.user_fullname,
	});

/** Whether the reader's system asks for less motion. */
export const lessMotion = () => Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);

/** Desk's own upload dialog, attaching to a record; `options` are the
 * dialog's own (a `method` to send the file to, `restrictions`). */
export function upload(doctype, name, done, options = {}) {
	return new (frappe().ui.FileUploader)({ doctype, docname: name, on_success: done, ...options });
}

/** Hear when any record of a doctype changes, as a list view does. */
export function followList(doctype, changed) {
	const realtime = frappe().realtime;
	const heard = (data) => data.doctype === doctype && changed(data);
	realtime.doctype_subscribe?.(doctype);
	realtime.on("list_update", heard);
	return () => realtime.off("list_update", heard);
}

/** A record's form, with frappe's Email open on it: the record's print
 * attached, its contact and templates offered. */
export function emailRecord(doctype, name) {
	const ours = (frm) => frm && frm.doctype === doctype && frm.doc.name === name;
	// The form says it's ready with frappe's own form-refresh.
	const ready = (_event, frm) => {
		if (!ours(frm)) return;
		window.$(document).off("form-refresh", ready);
		frm.email_doc();
	};
	window.$(document).on("form-refresh", ready);
	frappe().set_route("Form", doctype, name);
}

/** A whole number as the workspace writes numbers. */
export const count = (value) => window.format_number(value || 0, null, 0);

/** A user's name and picture, as desk keeps them for everyone. */
export const userInfo = (user) => {
	const info = frappe().user_info(user) || {};
	return { name: info.fullname || user, image: info.image };
};

/** The signed-in user. */
export const me = () => frappe().session.user;

/** A date in the past? Compared as desk's dates are, by day. */
export const isPast = (value) => Boolean(value) && value < frappe().datetime.get_today();

/** A short date, "3 Oct", for chips; the long form is `date`. */
/** A month as desk names it, in the reader's language: "October 2026". */
export const monthName = (value) =>
	value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { month: "long", year: "numeric" }) : "";

/** A month's short name, "Oct", for a dated line's ticks. */
export const shortMonth = (value) => (value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { month: "short" }) : "");
/** Today as desk has it, "2026-10-06". */
export const today = () => frappe().datetime.get_today();

export const shortDate = (value) => (value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { day: "numeric", month: "short" }) : "");

/** When, said as desk says it: "2 hours ago". */
export const ago = (value) => (value ? frappe().datetime.prettyDate(value) : "");

/**
 * What a mounted island needs from desk once: frappe-ui's own calls send the
 * CSRF token they find on `window`, and @framework/ui's live parts listen on
 * the socket they are given. Desk keeps both; this hands them over.
 */
export function deskSession() {
	if (!window.csrf_token && frappe()?.csrf_token) window.csrf_token = frappe().csrf_token;
	return { socket: frappe()?.realtime?.socket };
}

/** Keep a view's choice in the address, so a link or a reload opens it again. */
// The site's timezone and the reader's, as frappe's boot has them.
export function timeZone() {
  return (window.frappe && frappe.boot && frappe.boot.time_zone) || {};
}

export function setQuery(key, value) {
	const url = new URL(window.location.href);
	if (value) url.searchParams.set(key, value);
	else url.searchParams.delete(key);
	window.history.replaceState(window.history.state, "", url);
	// No route change for frappe to announce, so the OneAI panel is told
	// itself: what it offers follows the view (oneai.js where()).
	const oneai = window.onedesk && window.onedesk.oneai;
	if (oneai && oneai.panel) oneai.panel.moved(oneai.where());
}
