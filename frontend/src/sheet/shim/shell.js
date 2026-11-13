// The parts of Suite's shell the editor reaches for and the desk already does:
// the app switcher, theme and settings menus, the command palette.
import { computed } from "vue";
import { name } from "../../kit/desk";

export const useAppSwitcher = () => computed(() => null);
export const useThemeMenuOption = () => null;
export const useSettingsMenuOption = () => null;
export const useRootStore = () => ({ registerPaletteGroups: () => () => {} });
export const setupTheme = () => {};
export const appPageMeta = (title) => ({ title: title ? `${title} · ${name("one_sheet")}` : name("one_sheet") });
