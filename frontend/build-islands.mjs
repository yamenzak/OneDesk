import { fileURLToPath } from "node:url";
import { buildIslands } from "@framework/ui/vite/island";
import { lucideIconsPlugin } from "frappe-ui/vite/lucideIconsPlugin";
import { sheetSeams } from "./src/sheet/seams.mjs";
import { writerSeams } from "./src/writer/seams.mjs";
import { slideSeams } from "./src/slide/seams.mjs";

const COMPOSER = fileURLToPath(import.meta.resolve("@framework/ui/ActivityTimeline")).replace(
	/ActivityTimeline\/index\.ts$/,
	"Composer/index.ts"
);

export const ISLANDS = {
	"onedesk.project_part": "src/islands/project_part.js",
	"onedesk.template_part": "src/islands/template_part.js",
	"onedesk.stock": "src/islands/stock.js",
	"onedesk.one_home": "src/islands/one_home.js",
	"onedesk.home": "src/islands/home.js",
	"onedesk.head": "src/islands/head.js",
	"onedesk.books": "src/islands/books.js",
	"onedesk.crm": "src/islands/crm.js",
	"onedesk.hr": "src/islands/hr.js",
	"onedesk.to_order": "src/islands/to_order.js",
	"onedesk.supplier_items": "src/islands/supplier_items.js",
	"onedesk.item_part": "src/islands/item_part.js",
	"onedesk.check": "src/islands/check.js",
	"onedesk.workload": "src/islands/workload.js",
	"onedesk.floor": "src/islands/floor.js",
	"onedesk.factory": "src/islands/factory.js",
	"onedesk.quality": "src/islands/quality.js",
	"onedesk.timers": "src/islands/timers.js",
	"onedesk.counter": "src/islands/counter.js",
	"onedesk.boards": "src/islands/boards.js",
	"onedesk.workbook": "src/islands/workbook.js",
	"onedesk.document": "src/islands/document.js",
	"onedesk.presentation": "src/islands/presentation.js",
	"onedesk.intake": "src/islands/intake.js",
	"onedesk.onemail": "src/mail/island.js",
	"onedesk.onecloud": "src/islands/onecloud.js",
	"onedesk.oneadmin": "src/islands/oneadmin.js",
};

await buildIslands({
	app: "onedesk",
	root: import.meta.dirname,
	entries: ISLANDS,
	plugins: [slideSeams, sheetSeams, writerSeams, lucideIconsPlugin(), { name: "framework-ui-composer", enforce: "pre", resolveId: (source) => (source === "@framework/ui/Composer" ? COMPOSER : null) }],
	production: process.argv.includes("--production"),
	watch: process.argv.includes("--watch"),
});
