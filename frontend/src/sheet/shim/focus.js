// The element that has focus, looked for inside the shadow root the island
// mounts in: the page's own document.activeElement only ever names the host.
export function focused() {
	let found = document.activeElement;
	while (found?.shadowRoot?.activeElement) found = found.shadowRoot.activeElement;
	return found;
}
