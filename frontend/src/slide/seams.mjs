// Where the slides editor taken from Frappe Suite reaches into Suite's own shell,
// pointed at One's stand-ins in shim/ instead. The vendored files keep their
// imports as Suite wrote them, so a refresh from upstream is a copy. Only
// imports from this folder are answered here; the writer and the sheet have
// their own seams for the same names. VENDORED.md.
import { fileURLToPath } from "node:url";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const HERE = here("./");
const SHIM = here("./shim/");

const SEAMS = {
	"@/boot/session": "./shim/session.js",
	"@/stores/root": "./shim/shell.js",
	"@/utils/documentTitle": "./shim/shell.js",
	"@/utils/confirmLeave": "../sheet/shim/confirmLeave.js",
	"@/apps/slides/router": "./shim/router.js",
	"@/apps/slides/stores/offlineCopy": "./shim/offlineCopy.js",
	"@/apps/slides/utils/serviceWorker": "./shim/serviceWorker.js",
	"@/apps/slides/components/EditorNavbar.vue": "./shim/EditorNavbar.vue",
};

const ours = (importer) => Boolean(importer) && importer.startsWith(HERE);
const vendored = (importer) => ours(importer) && !importer.startsWith(SHIM);

export const slideSeams = {
	name: "onedesk-slide-seams",
	enforce: "pre",
	async resolveId(source, importer, options) {
		if (!ours(importer)) return null;
		if (SEAMS[source]) return here(SEAMS[source]);
		if (source === "frappe-ui" && vendored(importer)) return here("./shim/frappe-ui.js");
		if (!source.startsWith("@/apps/slides/")) return null;
		const [path, query] = source.slice("@/apps/slides/".length).split("?");
		const found = await this.resolve(here(`./${path.replace(/\/$/, "/index")}`), importer, { ...options, skipSelf: true });
		return found ? found.id + (query ? `?${query}` : "") : null;
	},
};
