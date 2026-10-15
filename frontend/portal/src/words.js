// frappe's translation, from the messages the boot carries in the reader's
// language (one/portal.py `boot`), as `__` reads everywhere else in One.
const messages = () => window.frappe?.boot?.__messages || {};

export function __(text, args, context) {
	const said = (context && messages()[`${text}:${context}`]) || messages()[text] || text;
	return String(said).replace(/\{(\d+)\}/g, (_, i) => (args || [])[Number(i)] ?? "");
}

/** The reader, their tabs and their account's pages, from the boot. */
export const boot = () => window.frappe?.boot || {};
