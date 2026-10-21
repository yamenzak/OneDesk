// Where the writer taken from Frappe Suite reaches into Suite's own shell,
// pointed at One's stand-ins in shim/ instead. The vendored files keep their
// imports as Suite wrote them, so a refresh from upstream is a copy. VENDORED.md.
import { fileURLToPath } from "node:url";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));

const SEAMS = {
	"@/boot/session": "./shim/session.js",
	"@/stores/root": "./shim/shell.js",
	"@/utils/documentTitle": "./shim/shell.js",
	"@/utils/confirmLeave": "../sheet/shim/confirmLeave.js",
	"@/apps/drive/sdk": "./shim/drive.js",
	"@/apps/writer/resources": "./shim/resources.js",
	"@/apps/writer/resources/": "./shim/resources.js",
	"@/apps/writer/composables/useYjs": "./shim/yjs.js",
	"@/apps/writer/router": "./shim/router.js",
};

export const writerSeams = {
	name: "onedesk-writer-seams",
	enforce: "pre",
	async resolveId(source, importer, options) {
		if (SEAMS[source]) return here(SEAMS[source]);
		if (!source.startsWith("@/apps/writer/")) return null;
		const [path, query] = source.slice("@/apps/writer/".length).split("?");
		const found = await this.resolve(here(`./${path.replace(/\/$/, "/index")}`), importer, { ...options, skipSelf: true });
		return found ? found.id + (query ? `?${query}` : "") : null;
	},
};
