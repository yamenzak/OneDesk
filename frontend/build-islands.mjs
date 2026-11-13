import { fileURLToPath } from "node:url";
import { buildIslands } from "@framework/ui/vite/island";
import { lucideIconsPlugin } from "frappe-ui/vite/lucideIconsPlugin";
import { sheetSeams } from "./src/sheet/seams.mjs";
import { docSeams } from "./src/doc/seams.mjs";
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
	"onedesk.hub": "src/islands/hub.js",
	"onedesk.marketplace": "src/islands/marketplace.js",
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
	"onedesk.onecloud": "src/cloud/island.js",
	"onedesk.onechat": "src/chat/island.js",
	"onedesk.oneadmin": "src/islands/oneadmin.js",
	"onedesk.oneadmin_servers": "src/islands/oneadmin_servers.js",
	"onedesk.oneadmin_server_part": "src/islands/oneadmin_server_part.js",
	"onedesk.oneadmin_billing": "src/islands/oneadmin_billing.js",
	"onedesk.oneadmin_releases": "src/islands/oneadmin_releases.js",
	"onedesk.oneadmin_status": "src/islands/oneadmin_status.js",
	"onedesk.oneadmin_sessions": "src/islands/oneadmin_sessions.js",
};

await buildIslands({
	app: "onedesk",
	root: import.meta.dirname,
	entries: ISLANDS,
	plugins: [slideSeams, sheetSeams, docSeams, lucideIconsPlugin(), { name: "framework-ui-composer", enforce: "pre", resolveId: (source) => (source === "@framework/ui/Composer" ? COMPOSER : null) }],
	production: process.argv.includes("--production"),
	watch: process.argv.includes("--watch"),
});
