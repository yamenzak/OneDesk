// The parts of Suite's shell the editor reaches for and the desk already does:
// the app switcher, theme and settings menus, the command palette.
import { computed } from "vue";

export const useAppSwitcher = () => computed(() => null);
export const useThemeMenuOption = () => null;
export const useSettingsMenuOption = () => null;
export const useRootStore = () => ({ registerPaletteGroups: () => () => {} });
export const setupTheme = () => {};
export const appPageMeta = (title) => ({ title: title ? `${title} · OneWorkbook` : "OneWorkbook" });
