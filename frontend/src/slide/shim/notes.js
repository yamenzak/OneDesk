// Whether the speaker notes under the slide are open; the toolbar stands above
// them when they are (components/Toolbar.vue, a One: edit).
import { computed, ref } from "vue";

export const notesOpen = ref(false);

// the drawer's height when open, and the closed bar's
export const NOTES_HEIGHT = 168;
export const NOTES_BAR = 36;

export const toolbarLift = computed(() => `${(notesOpen.value ? NOTES_HEIGHT : NOTES_BAR) + 8}px`);
