// Every OneDesk island, in one build, so they share one Vue and one frappe-ui
// (frappe/ui/README.md, "Desk islands"; docs/ISLANDS.md). An entry's name is
// the island's name: the build writes it into assets.json, which is frappe's
// registry (ui/island/decisions/0014). `bench build` runs this through the
// root package.json.
import { fileURLToPath } from "node:url";
import { buildIslands } from "@framework/ui/vite/island";

// frappe/ui's composers, which its package lists under no path of their own.
// Its root would bring every part it has (tests/guards, import the part).
const COMPOSER = fileURLToPath(import.meta.resolve("@framework/ui/ActivityTimeline")).replace(
	/ActivityTimeline\/index\.ts$/,
	"Composer/index.ts"
);

export const ISLANDS = {
	"onedesk.project": "src/islands/project.js",
	"onedesk.template": "src/islands/template.js",
	"onedesk.task": "src/islands/task.js",
	"onedesk.item": "src/islands/item.js",
	"onedesk.stock": "src/islands/stock.js",
	"onedesk.home": "src/islands/home.js",
	"onedesk.lots": "src/islands/lots.js",
	"onedesk.quotes": "src/islands/quotes.js",
	"onedesk.sent_out": "src/islands/sent_out.js",
	"onedesk.floor": "src/islands/floor.js",
	"onedesk.plant": "src/islands/plant.js",
	"onedesk.my_tasks": "src/islands/my_tasks.js",
	"onedesk.timers": "src/islands/timers.js",
};

await buildIslands({
	app: "onedesk",
	root: import.meta.dirname,
	entries: ISLANDS,
	plugins: [{ name: "framework-ui-composer", enforce: "pre", resolveId: (source) => (source === "@framework/ui/Composer" ? COMPOSER : null) }],
	production: process.argv.includes("--production"),
	watch: process.argv.includes("--watch"),
});
