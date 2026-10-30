import { fileURLToPath } from "node:url";
import { buildIslands } from "@framework/ui/vite/island";
import { lucideIconsPlugin } from "frappe-ui/vite/lucideIconsPlugin";
import { sheetSeams } from "./src/sheet/seams.mjs";
import { writerSeams } from "./src/writer/seams.mjs";

const COMPOSER = fileURLToPath(import.meta.resolve("@framework/ui/ActivityTimeline")).replace(
	/ActivityTimeline\/index\.ts$/,
	"Composer/index.ts"
);

export const ISLANDS = {
	"onedesk.project": "src/islands/project.js",
	"onedesk.template": "src/islands/template.js",
	"onedesk.item": "src/islands/item.js",
	"onedesk.stock": "src/islands/stock.js",
	"onedesk.one_home": "src/islands/one_home.js",
	"onedesk.home": "src/islands/home.js",
	"onedesk.books": "src/islands/books.js",
	"onedesk.crm": "src/islands/crm.js",
	"onedesk.hr": "src/islands/hr.js",
	"onedesk.lots": "src/islands/lots.js",
	"onedesk.to_order": "src/islands/to_order.js",
	"onedesk.supplier_items": "src/islands/supplier_items.js",
	"onedesk.check": "src/islands/check.js",
	"onedesk.workload": "src/islands/workload.js",
	"onedesk.quotes": "src/islands/quotes.js",
	"onedesk.sent_out": "src/islands/sent_out.js",
	"onedesk.upkeep": "src/islands/upkeep.js",
	"onedesk.floor": "src/islands/floor.js",
	"onedesk.plant": "src/islands/plant.js",
	"onedesk.timers": "src/islands/timers.js",
	"onedesk.counter": "src/islands/counter.js",
	"onedesk.display_layout": "src/islands/display_layout.js",
	"onedesk.workbook": "src/islands/workbook.js",
	"onedesk.document": "src/islands/document.js",
	"onedesk.intake": "src/islands/intake.js",
	"onedesk.onemail": "src/mail/island.js",
	"onedesk.onecloud": "src/islands/onecloud.js",
};

await buildIslands({
	app: "onedesk",
	root: import.meta.dirname,
	entries: ISLANDS,
	plugins: [sheetSeams, writerSeams, lucideIconsPlugin(), { name: "framework-ui-composer", enforce: "pre", resolveId: (source) => (source === "@framework/ui/Composer" ? COMPOSER : null) }],
	production: process.argv.includes("--production"),
	watch: process.argv.includes("--watch"),
});
