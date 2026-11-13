// The parts of Suite's shell the writer reaches for and the desk already does:
// the app switcher, theme and settings menus, the command palette.
import { computed, reactive } from "vue";

const root = reactive({ paletteOpen: false, registerPaletteGroups: () => () => {} });

export const useAppSwitcher = () => computed(() => null);
export const useThemeMenuOption = () => null;
export const useSettingsMenuOption = () => null;
export const useRootStore = () => root;
export const setupTheme = () => {};
export const appPageMeta = (title) => ({ title: title ? `${title} · OneDoc` : "OneDoc" });
