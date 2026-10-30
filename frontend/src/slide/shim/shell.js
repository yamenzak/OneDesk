// The parts of Suite's shell the slides editor reaches for and the desk already
// does: the command palette and the tab's title.
import { reactive } from "vue";

const root = reactive({ paletteOpen: false, registerPaletteGroups: () => () => {} });

export const useRootStore = () => root;
export const appPageMeta = (title) => ({ title: title ? `${title} · OneSlide` : "OneSlide" });
export const appDocumentTitle = (title) => (title ? `${title} · OneSlide` : "OneSlide");
