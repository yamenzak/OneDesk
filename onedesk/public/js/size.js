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
