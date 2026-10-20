// Pictures a cell shows through IMAGE(), such as the company's logo: each
// loaded once, and the grid painted again when one arrives.
const held = new Map();
const heard = new Set();

export function picture(url) {
	let img = held.get(url);
	if (!img) {
		img = new Image();
		img.onload = () => heard.forEach((paint) => paint());
		img.src = url;
		held.set(url, img);
	}
	return img.complete && img.naturalWidth ? img : null;
}

export function onPicture(paint) {
	heard.add(paint);
	return () => heard.delete(paint);
}
