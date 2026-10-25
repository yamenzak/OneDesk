// What OneMail's parts share: the kinds of folder, and how a date and a
// sender are said (one_mail/api.py).
import { __, call, clock, date, dateTime, msgprint, onedesk, shortDate, today } from "../kit";

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
	oneai: () => __("Linked by OneAI"),
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

export function framePage(content, pictures = false) {
	const escape = (text) => String(text).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
	let raw = content || "";
	if (!/<[a-z][\s\S]*>/i.test(raw)) raw = `<div style="white-space: pre-wrap">${escape(raw.replace(/\n{3,}/g, "\n\n").trim())}</div>`;
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
	const head = `<meta http-equiv="Content-Security-Policy" content="${policy}"><base target="_blank"><style>
			html { color-scheme: light; }
			body { margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #171717; overflow-wrap: anywhere; }
			img { max-width: 100%; height: auto; }
			blockquote { margin: 0 0 0 .6em; padding-left: .8em; border-left: 3px solid #e2e2e2; color: #525252; }
			pre { white-space: pre-wrap; }
			table { max-width: 100%; }
	</style>`;
	return { page: `<!doctype html><html><head>${head}</head><body dir="auto">${doc.body ? doc.body.innerHTML : ""}</body></html>`, held };
}
