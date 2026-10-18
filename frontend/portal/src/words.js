const messages = () => window.frappe?.boot?.__messages || {};

export function __(text, args, context) {
	const said = (context && messages()[`${text}:${context}`]) || messages()[text] || text;
	return String(said).replace(/\{(\d+)\}/g, (_, i) => (args || [])[Number(i)] ?? "");
}

export const boot = () => window.frappe?.boot || {};
