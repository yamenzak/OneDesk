
const frappe = () => window.frappe;

export function __(text, args, context) {
	if (window.__) return window.__(text, args, context);
	return String(text).replace(/\{(\d+)\}/g, (_, i) => (args || [])[Number(i)] ?? "");
}

export const call = (method, args = {}) => frappe().xcall(method, args);

// A method that answers GET only (frappe.whitelist(methods=["GET"])).
export const get = (method, args = {}) => frappe().xcall(method, args, "GET");

export function money(value, currency, decimals) {
	const said = window.format_currency(value || 0, currency, decimals);
	return window.onedesk?.shell?.ltr ? window.onedesk.shell.ltr(said) : said;
}

export const date = (value) => (value ? frappe().datetime.str_to_user(value) : "");

export const dateFormat = () => (frappe().boot.sysdefaults?.date_format || "yyyy-mm-dd").toUpperCase();

export const hours = (value) =>
	__("{0} h", [window.format_number(value || 0, null, Number(value) % 1 ? 1 : 0)]);

export const colors = (el, ...names) => {
	const styles = el ? getComputedStyle(el) : null;
	return names.map((name) => (styles ? styles.getPropertyValue(name).trim() : ""));
};

export const go = (route) => frappe().set_route(route);

export const goTo = (...route) => frappe().set_route(...route);

// A desk URL with a query string, which set_route's options cannot carry
// from every page (OneCloud's ?node=).
export const goToUrl = (url) => frappe().router.push_state(url);

export const userSettings = {
	get: (doctype) => frappe().model.user_settings.get(doctype),
	save: (doctype, key, value) => frappe().model.user_settings.save(doctype, key, value),
};

export const can = (action, doctype) => Boolean(frappe().model[`can_${action}`]?.(doctype));

export const canReport = (name) => Boolean(frappe().boot.allowed_reports?.[name]);

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

export function listen(event, heard) {
	frappe().realtime.on(event, heard);
	return () => frappe().realtime.off(event, heard);
}

export const newDoc = (doctype, values) => frappe().new_doc(doctype, values);

// The desk's quick entry for a new record called `name`; `made` gets it once saved.
export function quickEntry(doctype, name, made) {
	frappe().route_options = { name_field: name };
	frappe().ui.form.make_quick_entry(doctype, made);
}

// The desk's Advanced Search for a link; `picked` gets the name chosen.
export function linkSelector(doctype, txt, picked) {
	new (frappe().ui.form.LinkSelector)({ doctype, txt, target: { set_input: picked, $input: { trigger() {} } } });
}

export function newDocIn(doctype, values, projects) {
	if (!projects || projects.length < 2) return newDoc(doctype, values);
	const dialog = new (frappe().ui.Dialog)({
		title: __("New {0}", [__(doctype)]),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "project",
				options: "Project",
				label: __("Project"),
				reqd: 1,
				default: values.project,
				get_query: () => ({ filters: { name: ["in", projects] } }),
			},
		],
		primary_action_label: __("Continue"),
		primary_action: ({ project }) => {
			dialog.hide();
			newDoc(doctype, { ...values, project });
		},
	});
	dialog.show();
}

export const prompt = (fields, done, title, label) => frappe().prompt(fields, done, title, label);

export const confirm = (message, yes) => frappe().confirm(message, yes);
export const ask = (message, yes, no) =>
	new Promise((resolve) => frappe().confirm(message, () => resolve(true), () => resolve(false), yes, no));
export const andList = (items) => frappe().utils.comma_and(items);
export const escape = (text) => frappe().utils.escape_html(text);

export const onedesk = () => window.onedesk;

/** Who is signed in, as desk knows them: name, full name, picture and roles. */
export const person = () => {
	const desk = frappe();
	return { name: desk.session?.user || "", fullName: desk.session?.user_fullname || "", image: desk.user?.image?.() || "", roles: desk.user_roles || [] };
};

export const oneaiMark = "/assets/onedesk/images/oneai.svg";

export const oneaiOn = () => Boolean(window.onedesk?.apps?.ai?.());

// What the reader has selected on a page, for the OneAI panel to send with a
// question (public/js/oneai.js, where): null when nothing is.
export function aiSees(what) {
	if (window.onedesk?.oneai) window.onedesk.oneai.seen = what || null;
}

// The text field the reader just left: opening OneAI soon after writes in it
// (public/js/oneai.js, justLeft).
export function aiLeft(field) {
	if (window.onedesk?.oneai) window.onedesk.oneai.left = { at: Date.now(), field };
}

export const setValue = (doctype, name, fieldname, value) =>
	call("frappe.client.set_value", { doctype, name, fieldname, value });

export const insert = (doc) => call("frappe.client.insert", { doc });

export const assign = (doctype, name, users) =>
	call("frappe.desk.form.assign_to.add", { doctype, name, assign_to: users });
export const unassign = (doctype, name, user) =>
	call("frappe.desk.form.assign_to.remove", { doctype, name, assign_to: user });

export const comment = (doctype, name, content) =>
	call("frappe.desk.form.utils.add_comment", {
		reference_doctype: doctype,
		reference_name: name,
		content,
		comment_email: frappe().session.user,
		comment_by: frappe().session.user_fullname,
	});

export const lessMotion = () => Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);

export function upload(doctype, name, done, options = {}) {
	return new (frappe().ui.FileUploader)({ doctype, docname: name, on_success: done, ...options });
}

export function followList(doctype, changed) {
	const realtime = frappe().realtime;
	const heard = (data) => data.doctype === doctype && changed(data);
	realtime.doctype_subscribe?.(doctype);
	realtime.on("list_update", heard);
	return () => realtime.off("list_update", heard);
}

export function emailRecord(doctype, name) {
	const ours = (frm) => frm && frm.doctype === doctype && frm.doc.name === name;
	const ready = (_event, frm) => {
		if (!ours(frm)) return;
		window.$(document).off("form-refresh", ready);
		frm.email_doc();
	};
	window.$(document).on("form-refresh", ready);
	frappe().set_route("Form", doctype, name);
}

export const emailOn = (doctype, name, options) => onedesk().record.email(doctype, name, options);

export const count = (value) => window.format_number(value || 0, null, 0);

export const weekdays = () => {
	const first = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].indexOf(frappe().boot.sysdefaults?.first_day_of_the_week);
	return Array.from({ length: 7 }, (_, i) => (i + Math.max(first, 0)) % 7);
};

export const quantity = (value, uom) => {
	const said = window.format_number(value || 0, null, Number(value) % 1 ? 2 : 0);
	return uom ? __("{0} {1}", [said, __(uom)]) : said;
};

export const requires = (paths) => frappe().require(paths);

export const csrf = () => window.csrf_token || frappe().csrf_token || "";

export const openTab = (url = "") => window.open(url, "_blank");

export const jq = (el) => window.$(el);

export const viewWidth = () => window.innerWidth;

export function onResize(changed) {
	window.addEventListener("resize", changed);
	return () => window.removeEventListener("resize", changed);
}

// The page is being left: the desk routes elsewhere, or the tab goes out of
// sight (a desk page stays mounted when it is left).
export function onLeave(left) {
	const hidden = () => document.visibilityState === "hidden" && left();
	frappe().router?.on?.("change", left);
	document.addEventListener("visibilitychange", hidden);
	return () => {
		frappe().router?.off?.("change", left);
		document.removeEventListener("visibilitychange", hidden);
	};
}

export const userInfo = (user) => {
	const info = frappe().user_info(user) || {};
	return { name: info.fullname || user, image: info.image };
};

export const me = () => frappe().session.user;

export const mentionable = () =>
	Object.entries(frappe().boot.user_info || {})
		.filter(([user]) => user.includes("@") && !["Administrator", "Guest"].includes(user))
		.map(([user, info]) => ({ label: info.fullname || user, value: user }));

export const isPast = (value) => Boolean(value) && value < frappe().datetime.get_today();

export const fromToday = (value) => {
	const days = frappe().datetime.get_day_diff(value, frappe().datetime.get_today());
	if (!days) return __("today");
	if (days === 1) return __("tomorrow");
	if (days === -1) return __("yesterday");
	return days > 0 ? __("in {0} days", [days]) : __("{0} days ago", [-days]);
};

export const monthName = (value) =>
	value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { month: "long", year: "numeric" }) : "";

export const weekday = (value) =>
	value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { weekday: "long" }) : "";

export const clock = (value) =>
	value ? frappe().datetime.str_to_obj(value).toLocaleTimeString(frappe().boot.lang || undefined, { hour: "2-digit", minute: "2-digit" }) : "";

export const shortMonth = (value) => (value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { month: "short" }) : "");
export const today = () => frappe().datetime.get_today();

export const shortDate = (value) => (value ? frappe().datetime.str_to_obj(value).toLocaleDateString(frappe().boot.lang || undefined, { day: "numeric", month: "short" }) : "");

export const duration = (seconds, { seconds: withSeconds = true } = {}) =>
	frappe().utils.get_formatted_duration(Math.max(Math.round(seconds || 0), 0), { hide_days: 1, hide_seconds: withSeconds ? 0 : 1 }) || "0m";

export const secondsSince = (value) =>
	value ? (frappe().datetime.system_datetime(true) - frappe().datetime.str_to_obj(value)) / 1000 : 0;

export const ago = (value) => (value ? frappe().datetime.prettyDate(value) : "");

export function deskSession() {
	if (!window.csrf_token && frappe()?.csrf_token) window.csrf_token = frappe().csrf_token;
	return { socket: frappe()?.realtime?.socket };
}

export function timeZone() {
  return frappe()?.boot?.time_zone || {};
}

export function setQuery(key, value) {
	const url = new URL(window.location.href);
	if (value) url.searchParams.set(key, value);
	else url.searchParams.delete(key);
	window.history.replaceState(window.history.state, "", url);
	const oneai = window.onedesk && window.onedesk.oneai;
	if (oneai && oneai.panel) oneai.panel.moved(oneai.where());
}

export function barcode(value, format, options = {}) {
	const control = frappe().ui.form.make_control({
		parent: document.createElement("div"),
		df: { fieldtype: "Barcode", fieldname: "barcode", options: JSON.stringify({ format, ...options }) },
		render_input: true,
	});
	return control.get_barcode_html(value) || "";
}

export const docfield = (doctype, fieldname) =>
	new Promise((done) => frappe().model.with_doctype(doctype, () => done(frappe().meta.get_docfield(doctype, fieldname))));

export const dialog = (options) => new (frappe().ui.Dialog)(options);

export const alert = (message, indicator = "green") => frappe().show_alert({ message, indicator });

export const formatted = (value, df, doc) => String(frappe().format(value, df, { inline: true, only_value: true }, doc) ?? "");

export const symbol = (name) => {
  const found = document.getElementById(`icon-${name}`);
  return found ? { viewBox: found.getAttribute("viewBox"), html: found.innerHTML } : null;
};

// Where on the window a part of an island goes (docs/WINDOW.md, The parts):
// the nav pane under the view's row, the details pane, the command row or the
// views at its end. Null when the island is not on a window (in a dialog).
export function windowPart(win, part, { key = "page", width } = {}) {
	if (!win) return null;
	const $at = {
		nav: () => win.nav_slot(),
		details: () => win.details({ key, width }),
		commands: () => win.group("own"),
		views: () => win.views_slot(),
	}[part]?.();
	return $at && $at[0] ? $at[0] : null;
}

export const copyText = (text) => frappe().utils.copy_to_clipboard(text);

export const msgprint = (message, title) => frappe().msgprint(title ? { title, message } : message);

export const intakeOn = () => Boolean(window.onedesk?.apps?.intake?.());

// A record's desk address, as frappe's router writes it.
export const recordRoute = (doctype, name) => `/desk/${frappe().router.slug(doctype)}/${encodeURIComponent(name)}`;

export const hasRole = (role) => Boolean(frappe().user.has_role(role));

export const dateTime = (value) => (value ? frappe().datetime.str_to_user(value) : "");

export const fileSize = (bytes) => (window.onedesk?.size ? window.onedesk.size(bytes) : "");

// frappe's mail composer, told when it closes.
export function compose(options, closed) {
	const composer = new (frappe().views.CommunicationComposer)(options);
	if (closed) composer.dialog.$wrapper.on("hidden.bs.modal", closed);
	return composer;
}

// frappe's toast, with one action on it.
export function toast(message, action = null, duration = 8000) {
	const shown = frappe().ui.toast({
		message,
		duration,
		...(action ? { action: { label: action.label, onclick: () => (shown.dismiss(), action.onClick()) } } : {}),
	});
	return shown;
}

// The window's own search box, in its address row.
export function windowSearch(win, { placeholder = "", title = "", onInput, onKey } = {}) {
	if (!win) return null;
	const $input = win.search({
		placeholder,
		on_input: onInput,
		on_key: onKey,
	});
	if (title) $input.attr("title", title);
	return {
		set: (value) => $input.val(value || ""),
		focus: () => $input.trigger("focus"),
		placeholder: (text) => $input.attr("placeholder", text),
		element: $input[0],
	};
}

// The window's tree (window/nav_tree.js): rows in this view's nav pane, or,
// with no window, in a box of the desk's own that the host gave (OneCloud's
// picker). Rows and handlers as nav_tree.js says; `lucide-` is dropped from
// an icon, since the desk names its sprite's icons bare. Returns `set(rows)`.
export function windowTree(at, { label = "", pick, twist, over, leave, drop } = {}) {
	if (!at) return null;
	const spec = { label, pick, twist, over, leave, drop, rows: [] };
	const tree = at.tree ? at.tree(spec) : new window.onedesk.window.Tree(window.$(at), spec);
	return {
		set: (rows) => tree.set({ rows: rows.map((row) => ({ ...row, icon: row.icon && row.icon.replace(/^lucide-/, "") })) }),
	};
}

// A button at the end of the rail's head while this view is on screen
// (window/nav_tree.js); `icon` is a lucide name.
export const windowHeadAction = (win, { icon, title, onClick }) =>
	win && win.head_action({ icon: icon.replace(/^lucide-/, ""), title, click: onClick });

// Meters at the foot of this view's nav pane (window/nav_tree.js).
export const windowMeters = (win, rows) => win && win.meters(rows);

// What the window does for its own Up, Refresh and typed paths, and its
// status row.
export const windowHandles = (win, handlers) => win && win.view(handlers);
export const windowStatus = (win, text) => win && win.status(text);
export const windowCan = (win, can) => win && win.can(can);

// An event published to a doctype's room (frappe's get_doctype_room), heard
// while the island is up.
export function listenIn(doctype, event, heard) {
	frappe().realtime.doctype_subscribe(doctype);
	frappe().realtime.on(event, heard);
	return () => frappe().realtime.off(event, heard);
}

// The page's breadcrumbs and title, for an island that walks a tree of its
// own (OneCloud's folders).
export function setCrumbs(items, title) {
	const page = frappe().get_current_page?.() || frappe().container?.page?.page;
	page?.set_breadcrumbs?.(items);
	if (title) frappe().utils.set_title(title);
}

// OneAI's panel follows where the reader is (oneai.js, where).
export function aiMoved() {
	const oneai = window.onedesk && window.onedesk.oneai;
	if (oneai && oneai.panel) oneai.panel.moved(oneai.where());
}
