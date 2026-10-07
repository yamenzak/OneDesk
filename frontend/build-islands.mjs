// Every OneDesk island, in one build, so they share one Vue and one frappe-ui
// (frappe/ui/README.md, "Desk islands"; docs/ISLANDS.md). Each entry is named
// in hooks.py `ui_islands`. `bench build` runs this through the root
// package.json.
import { fileURLToPath } from "node:url";
import { buildIslands } from "@framework/ui/vite/island";

// frappe/ui's composers, which its package lists under no path of their own.
// Its root would also bring its fields, which need a newer frappe-ui (#111).
const COMPOSER = fileURLToPath(import.meta.resolve("@framework/ui/ActivityTimeline")).replace(
	/ActivityTimeline\/index\.ts$/,
	"Composer/index.ts"
);

export const ISLANDS = {
	onedesk_project: "src/islands/project.js",
	onedesk_template: "src/islands/template.js",
};

await buildIslands({
	app: "onedesk",
	root: import.meta.dirname,
	entries: ISLANDS,
	plugins: [{ name: "framework-ui-composer", enforce: "pre", resolveId: (source) => (source === "@framework/ui/Composer" ? COMPOSER : null) }],
	production: process.argv.includes("--production"),
	watch: process.argv.includes("--watch"),
});
