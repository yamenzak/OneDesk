
const frappe = () => window.frappe;

export function __(text, args, context) {
	if (window.__) return window.__(text, args, context);
	return String(text).replace(/\{(\d+)\}/g, (_, i) => (args || [])[Number(i)] ?? "");
}

export const call = (method, args = {}) => frappe().xcall(method, args);

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

export const jq = (el) => window.$(el);

export const viewWidth = () => window.innerWidth;

export function onResize(changed) {
	window.addEventListener("resize", changed);
	return () => window.removeEventListener("resize", changed);
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
