// The presenter view and the audience's window, kept in step (AGENTS.md,
// Presenting). The presenter's tab shows the notes, the next slide and the
// time; the audience's window, opened beside it, plays the slideshow. They
// talk over the browser's own BroadcastChannel, so nothing leaves the
// computer and it works with no network at all.
import { ref } from "vue";

import { openPopup } from "../../kit/desk";

// this tab is showing the presenter view
export const presenting = ref(false);

// this window is the audience's: a slideshow that need not fill the screen
// and is driven from the presenter view
export const audience = ref(false);

let channel = null;

export function link(id, heard) {
	unlink();
	channel = new BroadcastChannel(`oneslide:${id}`);
	channel.onmessage = (event) => heard(event.data || {});
}

export const say = (said) => channel?.postMessage(said);

export function unlink() {
	channel?.close();
	channel = null;
}

// the presenter view here, and the slideshow in a window of its own
export function startPresenter(id, index) {
	presenting.value = true;
	openPopup(`/desk/presentation/${encodeURIComponent(id)}?audience=1&slide=${index + 1}`, `oneslide-audience-${id}`);
}
