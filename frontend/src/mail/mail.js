// What OneMail's parts share: the kinds of folder, and how a date and a
// sender are said (one_mail/api.py).
import { __, call, clock, date, dateTime, msgprint, name, onedesk, shortDate, today } from "../kit";

export const API = "onedesk.one_mail.api.";
export const ACT = "onedesk.one_mail.actions.";

export const KINDS = {
	Inbox: ["lucide-inbox", () => __("Inbox")],
	Drafts: ["lucide-file-pen-line", () => __("Drafts")],
	Sent: ["lucide-send", () => __("Sent")],
	Archive: ["lucide-archive", () => __("Archive")],
	Junk: ["lucide-shield-alert", () => __("Junk")],
	Trash: ["lucide-trash-2", () => __("Trash")],
	Other: ["lucide-folder", null],
};

export const FILED_BY = {
	contact: () => __("Linked by contact"),
	address: () => __("Linked by email address"),
	thread: () => __("Linked by conversation"),
	text: () => __("Mentioned in the message"),
	manual: () => __("Linked manually"),
	rule: () => __("Linked by a rule"),
	oneai: () => __("Linked by {0}", [name("one_ai")]),
};

export const kindOf = (folder) => KINDS[folder.kind] || KINDS.Other;

export function folderLabel(folder) {
	const [, label] = kindOf(folder);
	if (label && folder.kind !== "Other") return label();
	return folder.label || folder.path;
}

export function depth(folder) {
	if (!folder.delimiter || folder.kind !== "Other") return 0;
	return folder.path.split(folder.delimiter).length - 1;
}

const PROVIDERS = {
	"gmail.com": "Gmail",
	"googlemail.com": "Gmail",
	"outlook.com": "Outlook",
	"hotmail.com": "Outlook",
	"live.com": "Outlook",
	"msn.com": "Outlook",
	"icloud.com": "iCloud",
	"me.com": "iCloud",
	"yahoo.com": "Yahoo",
};

// A mailbox in the sidebar: the workspace's, the address the workspace gave
// the person (System), one at a company domain (Organization), a private one
// by its provider or domain, or a shared one's address.
export function called(box) {
	if (box.workspace) return __("Workspace");
	if (box.shared) return box.email;
	if (box.hosted) return __("System");
	if (box.connected && !box.private) return __("Organization");
	const domain = (box.email || "").split("@").pop().toLowerCase();
	return PROVIDERS[domain] || domain;
}

// Today's mail by its time, older by its day.
export function when(value, long = false) {
	if (!value) return "";
	if (long) return dateTime(value);
	if (value.slice(0, 10) === today()) return clock(value);
	if (value.slice(0, 4) === today().slice(0, 4)) return shortDate(value.slice(0, 10));
	return date(value.slice(0, 10));
}

export function who(item) {
	if (item.sent && item.recipients) {
		const first = item.recipients.split(",")[0].trim();
		return __("To {0}", [first.replace(/<.*>/, "").trim() || first]);
	}
	return item.sender_name || item.sender || __("Unknown sender");
}

// Who a new mail, a reply and a forward come from, and the reply and forward
// themselves: public/js/one_mail/mail_compose.js, which OneAI's reply card uses too.
export const sender = (boxes, box) => onedesk().mail.sender(boxes, box);

export function reply(boxes, messages, from, { all = false } = {}, closed) {
	const composer = onedesk().mail.reply(boxes, messages, from, { all });
	if (closed) composer.dialog.$wrapper.on("hidden.bs.modal", closed);
	return composer;
}

export function forward(messages, from, closed) {
	const composer = onedesk().mail.forward(messages, from, when(messages[messages.length - 1].communication_date, true));
	if (closed) composer.dialog.$wrapper.on("hidden.bs.modal", closed);
	return composer;
}

export const noSender = () => msgprint(__("None of your mailboxes can send email"));

export const names = (account, threads, folder = null) => call(API + "names", { account, threads, folder });

// A message's own HTML as a page for a sandboxed frame: no scripts, frames,
// forms or handlers, a policy that lets nothing load, and pictures from
// elsewhere held back until the reader asks for them (they tell a sender the
// mail was read). The page's own colours are a printed letter's, whatever the
// reader's theme, as the sender wrote it.

// A plain-text message as its sender wrote it. Frappe stores one with its
// characters escaped and every line break doubled (frappe/email/receive.py),
// for its own timeline; a text where no line break stands alone is halved
// back.
export function plainText(stored) {
	let text = new DOMParser().parseFromString(`<pre>${stored || ""}</pre>`, "text/html").body.textContent;
	if (!/(^|[^\n])\n(?!\n)/.test(text)) text = text.replace(/\n\n/g, "\n");
	return text.replace(/\n{3,}/g, "\n\n").trim();
}

export function framePage(content, pictures = false, dark = false) {
	const escape = (text) => String(text).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
	let raw = content || "";
	if (!/<[a-z][\s\S]*>/i.test(raw)) raw = `<div style="white-space: pre-wrap">${escape(plainText(raw))}</div>`;
	const doc = new DOMParser().parseFromString(raw, "text/html");
	doc.querySelectorAll("script, iframe, object, embed, form, meta[http-equiv], link[rel=import]").forEach((el) => el.remove());
	doc.querySelectorAll("*").forEach((el) => {
		for (const attr of [...el.attributes]) if (/^on/i.test(attr.name)) el.removeAttribute(attr.name);
	});
	let held = 0;
	const here = document.location.origin;
	doc.querySelectorAll("img[src], img[srcset], [background]").forEach((el) => {
		const src = el.getAttribute("src") || el.getAttribute("background") || "";
		if (/^(https?:)?\/\//i.test(src) && !src.startsWith(here) && !pictures) {
			el.removeAttribute("src");
			el.removeAttribute("srcset");
			el.removeAttribute("background");
			held++;
		}
	});
	const policy = `default-src 'none'; img-src 'self' data: ${pictures ? "https: http:" : ""}; style-src 'unsafe-inline'; font-src 'self' data:`;
	const painted = dark && /bgcolor|background|<style|color\s*:/i.test(raw);
	const ink = dark && !painted ? { scheme: "dark", text: "#e5e5e5", quote: "#404040", quoted: "#a3a3a3" } : { scheme: "light", text: "#171717", quote: "#e2e2e2", quoted: "#525252" };
	const head = `<meta http-equiv="Content-Security-Policy" content="${policy}"><base target="_blank"><style>
			html { color-scheme: ${ink.scheme}; ${painted ? "background: #fff;" : ""} }
			body { margin: 0; ${painted ? "padding: 12px;" : ""} font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: ${ink.text}; overflow-wrap: anywhere; }
			img { max-width: 100%; height: auto; }
			blockquote { margin: 0 0 0 .6em; padding-left: .8em; border-left: 3px solid ${ink.quote}; color: ${ink.quoted}; }
			pre { white-space: pre-wrap; }
			table { max-width: 100%; }
	</style>`;
	return { page: `<!doctype html><html><head>${head}</head><body dir="auto">${doc.body ? doc.body.innerHTML : ""}</body></html>`, held };
}
