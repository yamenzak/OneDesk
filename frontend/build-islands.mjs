// Every OneDesk island, in one build, so they share one Vue and one frappe-ui
// (frappe/ui/README.md, "Desk islands"; docs/ISLANDS.md). Each entry is named
// in hooks.py `ui_islands`. `bench build` runs this through the root
// package.json.
import { buildIslands } from "@framework/ui/vite/island";

export const ISLANDS = {
	onedesk_project: "src/islands/project.js",
	onedesk_template: "src/islands/template.js",
};

await buildIslands({
	app: "onedesk",
	root: import.meta.dirname,
	entries: ISLANDS,
	production: process.argv.includes("--production"),
	watch: process.argv.includes("--watch"),
});
