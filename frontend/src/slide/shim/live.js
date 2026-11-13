// Present Live: while the presenter plays the slideshow, everyone on the
// presentation's OneCloud links follows the slide they are on
// (one_deck/shared.py; the guest page is public/js/one_deck/viewer.js).
// It ends with the slideshow.
import { ref, watch } from "vue";
import { alert, call } from "../../kit/desk";
import { __ } from "./words.js";

export const liveOn = ref(false);
let presentation = "";
let timer = null;

export function beginLive(name, index) {
	presentation = name;
	liveOn.value = true;
	at(index);
	alert(__("Presenting live: everyone with a link to this presentation follows your slides."));
}

// the slide shown, told once it has settled
export function at(index) {
	if (!liveOn.value || !presentation) return;
	clearTimeout(timer);
	timer = setTimeout(() => call("onedesk.one_deck.shared.present_live", { name: presentation, slide: index }), 150);
}

export function endLive() {
	if (!liveOn.value) return;
	liveOn.value = false;
	clearTimeout(timer);
	call("onedesk.one_deck.shared.stop_live", { name: presentation });
}

// the slideshow's own page tells `at` each slide (pages/Slideshow.vue, a One: edit)
export function followSlideshow(inSlideShowMode) {
	watch(inSlideShowMode, (on, was) => was && !on && endLive());
}
