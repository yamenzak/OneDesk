// Where the editor taken from Frappe Suite reaches into Suite's own shell,
// pointed at One's stand-ins in shim/ instead. The vendored files keep their
// imports as Suite wrote them, so a refresh from upstream is a copy. VENDORED.md.
import { fileURLToPath } from "node:url";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));

const SEAMS = {
	"@/boot/session": "./shim/session.js",
	"@/composables/useAppSwitcher": "./shim/shell.js",
	"@/composables/useThemeMenuOption": "./shim/shell.js",
	"@/composables/useSettingsMenuOption": "./shim/shell.js",
	"@/stores/root": "./shim/shell.js",
	"@/utils/setupTheme": "./shim/shell.js",
	"@/utils/documentTitle": "./shim/shell.js",
	"@/utils/confirmLeave": "./shim/confirmLeave.js",
	"@/apps/drive/components/InlineRenameInput.vue": "./shim/InlineRenameInput.vue",
	"~icons/lucide/globe": "./shim/GlobeIcon.vue",
	"@hocuspocus/provider": "./shim/hocuspocus.js",
	"socket.io-client": "./shim/socket.js",
};

export const sheetSeams = {
	name: "onedesk-sheet-seams",
	enforce: "pre",
	resolveId(source) {
		if (SEAMS[source]) return here(SEAMS[source]);
		if (source.endsWith("/collab/realtime-adapter.js")) return here("./shim/live.js");
		if (source.startsWith("@/apps/sheets/")) return here(`./${source.slice("@/apps/sheets/".length)}`);
		return null;
	},
};
