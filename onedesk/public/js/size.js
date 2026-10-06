// A size in bytes as somebody says it out loud, "1.4 MB". The number goes
// through frappe's format_number, so it reads in the workspace's number
// format. Files are counted in 1024s, as an explorer counts them; a plan is
// sold in 1000s, so its pages pass base 1000. Loaded on desk and on the
// portal pages that take files.
frappe.provide("onedesk");

onedesk.size = (bytes, base = 1024) => {
	let left = Number(bytes || 0);
	if (!left) return "";
	const units = [__("B"), __("KB"), __("MB"), __("GB"), __("TB")];
	let at = 0;
	while (left >= base && at < units.length - 1) {
		left /= base;
		at += 1;
	}
	const tenths = at && left < 10 && Math.round(left * 10) % 10;
	return `${format_number(left, null, tenths ? 1 : 0)} ${units[at]}`;
};
