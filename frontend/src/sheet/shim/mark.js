// A mark from the desk's sprite, drawn whole: the editor sits in a shadow root,
// where a <use> pointing at the document's sprite draws nothing.
export function mark(name) {
	const symbol = document.getElementById(`icon-${name}`);
	if (!symbol) return "";
	const box = symbol.getAttribute("viewBox") || "0 0 192 192";
	return `<svg viewBox="${box}" aria-hidden="true">${symbol.innerHTML}</svg>`;
}
