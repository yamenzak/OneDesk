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

/** Money as desk formats it, to the workspace's currency precision (or
 * `decimals`, as a chart's axis takes whole amounts), kept left-to-right in Arabic. */
export function money(value, currency, decimals) {
	const said = window.format_currency(value || 0, currency, decimals);
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

/** Whether the reader may open a report, from the reports frappe boots them. */
export const canReport = (name) => Boolean(frappe().boot.allowed_reports?.[name]);

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
/** frappe's confirm as a promise: true for its first button, false for the
 * other or closing it. `yes` and `no` name the two buttons. */
export const ask = (message, yes, no) =>
	new Promise((resolve) => frappe().confirm(message, () => resolve(true), () => resolve(false), yes, no));
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

/** frappe's Email dialog on a record shown on a page (record.js
 * `onedesk.record.email`): a new email, or with `email` a reply to it. */
export const emailOn = (doctype, name, options) => onedesk().record.email(doctype, name, options);

/** A whole number as the workspace writes numbers. */
export const count = (value) => window.format_number(value || 0, null, 0);

// The days of the week from the one the workspace starts its week on (System
// Settings), each as Python's weekday() numbers it (0 is Monday).
export const weekdays = () => {
	const first = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].indexOf(frappe().boot.sysdefaults?.first_day_of_the_week);
	return Array.from({ length: 7 }, (_, i) => (i + Math.max(first, 0)) % 7);
};

/** How many, with its unit if given, to two places only when it has a
 * fraction: "3,308 Meter", "1.30 Square Meter". */
export const quantity = (value, uom) => {
	const said = window.format_number(value || 0, null, Number(value) % 1 ? 2 : 0);
	return uom ? __("{0} {1}", [said, __(uom)]) : said;
};

/** An amount without its currency, as the workspace writes numbers: for a
 * table whose currency is said once above it. */
export const plain = (value) => window.format_number(value || 0, null, 2);

/** Desk's own scripts and styles, loaded once (`frappe.require`). */
export const requires = (paths) => frappe().require(paths);

/** Desk's jQuery around an element, for desk's widgets that take one. */
export const jq = (el) => window.$(el);

/** How wide the window is. */
export const viewWidth = () => window.innerWidth;

/** Call `changed` when the window is resized; returns how to stop. */
export function onResize(changed) {
	window.addEventListener("resize", changed);
	return () => window.removeEventListener("resize", changed);
}

/** A user's name and picture, as desk keeps them for everyone. */
export const userInfo = (user) => {
	const info = frappe().user_info(user) || {};
	return { name: info.fullname || user, image: info.image };
};

/** The signed-in user. */
export const me = () => frappe().session.user;

/** Everyone desk's comment box offers to @-mention, as `{ label, value }`. */
export const mentionable = () =>
	Object.entries(frappe().boot.user_info || {})
		.filter(([user]) => user.includes("@") && !["Administrator", "Guest"].includes(user))
		.map(([user, info]) => ({ label: info.fullname || user, value: user }));

/** A date in the past? Compared as desk's dates are, by day. */
export const isPast = (value) => Boolean(value) && value < frappe().datetime.get_today();

/** How far a day is from today, as words: "in 24 days", "3 days ago", "today". */
export const fromToday = (value) => {
	const days = frappe().datetime.get_day_diff(value, frappe().datetime.get_today());
	if (!days) return __("today");
	if (days === 1) return __("tomorrow");
	if (days === -1) return __("yesterday");
	return days > 0 ? __("in {0} days", [days]) : __("{0} days ago", [-days]);
};

/** A short date, "3 Oct", for chips; the long form is `date`. */
/** A month as desk names it, in the reader's language: "October 2026". */
export const monthName = (value) =>
	value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { month: "long", year: "numeric" }) : "";

/** A day's name, "Thursday", in the reader's language. */
export const weekday = (value) =>
	value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { weekday: "long" }) : "";

/** A time of day, "14:05", as the reader's language writes it. */
export const clock = (value) =>
	value ? frappe().datetime.str_to_obj(value).toLocaleTimeString(frappe().boot.lang || undefined, { hour: "2-digit", minute: "2-digit" }) : "";

/** A month's short name, "Oct", for a dated line's ticks. */
export const shortMonth = (value) => (value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { month: "short" }) : "");
/** Today as desk has it, "2026-10-06". */
export const today = () => frappe().datetime.get_today();

export const shortDate = (value) => (value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { day: "numeric", month: "short" }) : "");

/** A length of time, "1h 5m 20s", as desk writes a Duration. */
export const duration = (seconds, { seconds: withSeconds = true } = {}) =>
	frappe().utils.get_formatted_duration(Math.max(Math.round(seconds || 0), 0), { hide_days: 1, hide_seconds: withSeconds ? 0 : 1 }) || "0m";

/** Seconds from a moment the server wrote, in the site's time, until now. */
export const secondsSince = (value) =>
	value ? (frappe().datetime.system_datetime(true) - frappe().datetime.str_to_obj(value)) / 1000 : 0;

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

// The site's timezone and the reader's, as frappe's boot has them.
export function timeZone() {
  return frappe()?.boot?.time_zone || {};
}

/** Keep a view's choice in the address, so a link or a reload opens it again. */
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

/** A barcode as desk's Barcode field draws it (frappe.ui.form.ControlBarcode),
 * as SVG markup, or "" when the value does not fit the format. `options` are
 * JsBarcode's. */
export function barcode(value, format, options = {}) {
	const control = frappe().ui.form.make_control({
		parent: document.createElement("div"),
		df: { fieldtype: "Barcode", fieldname: "barcode", options: JSON.stringify({ format, ...options }) },
		render_input: true,
	});
	return control.get_barcode_html(value) || "";
}

/** A field of a doctype as desk has it, its doctype loaded first. */
export const docfield = (doctype, fieldname) =>
	new Promise((done) => frappe().model.with_doctype(doctype, () => done(frappe().meta.get_docfield(doctype, fieldname))));

/** Desk's own dialog, with frappe's fields. */
export const dialog = (options) => new (frappe().ui.Dialog)(options);

/** Desk's alert in the corner, as a form's save shows "Saved". */
export const alert = (message, indicator = "green") => frappe().show_alert({ message, indicator });

/** A value as desk's form writes it for its field, read-only and inline. */
/** (A whole number comes back as a number, and 0 must still show.) */
export const formatted = (value, df, doc) => String(frappe().format(value, df, { inline: true, only_value: true }, doc) ?? "");
