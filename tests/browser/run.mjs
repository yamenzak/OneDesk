// Opens every screen in screens.mjs on the demo workspace, as its person, and
// says which did not show what it should, threw in the browser, or refused.
//
//     ONE_URL=http://onedesk.localhost:8002 ONE_DEMO_PASSWORD=… node tests/browser/run.mjs [path-part]
//
// Playwright is not a dependency of the app: point PLAYWRIGHT_FROM at a
// directory whose node_modules has it, and CHROMIUM at a browser if
// Playwright's own is not installed. ONE_SHOTS names a folder for a
// screenshot of each screen.
//
// A screen's `panel` says whether the module's panel is open on a desktop
// (docs/PASSOVER.md, The panel), `phone` the places its breadcrumb lists as a
// menu on a phone, and `menu` the places it lists on a desktop.
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

import { NEVER, SCREENS } from "./screens.mjs";

const require = createRequire(join(process.env.PLAYWRIGHT_FROM || process.cwd(), "noop.js"));
const { chromium } = require("playwright");

const BASE = process.env.ONE_URL || "http://onedesk.localhost:8002";
const PASSWORD = process.env.ONE_DEMO_PASSWORD;
const SHOTS = process.env.ONE_SHOTS;
const ONLY = process.argv[2];
if (!PASSWORD) throw new Error("Set ONE_DEMO_PASSWORD to the demo people's password.");
if (SHOTS) mkdirSync(SHOTS, { recursive: true });

const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
const failed = [];
const people = new Map();

async function as(who, phone = false) {
	const key = `${who}${phone ? " on a phone" : ""}`;
	if (!people.has(key)) {
		const viewport = phone ? { width: 390, height: 844 } : { width: 1440, height: 900 };
		const context = await browser.newContext({ viewport });
		const signed = await context.request.post(`${BASE}/api/method/login`, { form: { usr: who, pwd: PASSWORD } });
		if (!signed.ok()) throw new Error(`${who} could not sign in (${signed.status()})`);
		people.set(key, context);
	}
	return people.get(key);
}

// Whether the module's panel is out beside the page.
const panel_open = (page) =>
	page.evaluate(() => {
		const panel = document.querySelector(".body-sidebar-container");
		return !!panel && panel.offsetParent !== null && panel.classList.contains("expanded");
	});

// What is wrong with the breadcrumb's menu of places, on a phone or not.
async function crumb_menu(screen, labels, phone) {
	const where = phone ? " on a phone" : "";
	const page = await (await as(screen.who, phone)).newPage();
	try {
		await page.goto(BASE + screen.path, { waitUntil: "networkidle", timeout: 60000 });
		if (phone && (await panel_open(page))) return ["has its panel out on a phone"];
		const crumb = page.locator(".navbar-breadcrumbs li.one-places").filter({ visible: true }).first();
		try {
			await crumb.waitFor({ state: "visible", timeout: 15000 });
		} catch {
			return [`has no menu in its breadcrumb${where}`];
		}
		await crumb.click();
		const missing = [];
		for (const label of labels) {
			try {
				await page.getByRole("menuitem", { name: label, exact: true }).waitFor({ state: "visible", timeout: 5000 });
			} catch {
				missing.push(`breadcrumb menu${where} does not list "${label}"`);
			}
		}
		return missing;
	} finally {
		await page.close();
	}
}

for (const screen of SCREENS.filter((one) => !ONLY || one.path.includes(ONLY))) {
	const page = await (await as(screen.who)).newPage();
	const thrown = [];
	page.on("pageerror", (error) => thrown.push(error.message));
	const wrong = [];
	try {
		await page.goto(BASE + screen.path, { waitUntil: "networkidle", timeout: 60000 });
		for (const text of screen.sees) {
			try {
				await page.getByText(text, { exact: false }).filter({ visible: true }).first().waitFor({ state: "visible", timeout: 15000 });
			} catch {
				wrong.push(`does not show "${text}"`);
			}
		}
		const body = await page.locator("body").innerText();
		wrong.push(...NEVER.filter((text) => body.includes(text)).map((text) => `says "${text}"`));
		wrong.push(...thrown.map((message) => `threw: ${message.slice(0, 200)}`));
		if (screen.panel !== undefined && (await panel_open(page)) !== screen.panel)
			wrong.push(screen.panel ? "has its panel shut" : "has its panel out");
		if (screen.phone) wrong.push(...(await crumb_menu(screen, screen.phone, true)));
		if (screen.menu) wrong.push(...(await crumb_menu(screen, screen.menu, false)));
		if (SHOTS) await page.screenshot({ path: join(SHOTS, `${screen.path.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "")}.png`) });
	} catch (error) {
		wrong.push(`did not open: ${error.message.split("\n")[0]}`);
	}
	await page.close();
	console.log(`${wrong.length ? "FAIL" : "ok  "}  ${screen.who.padEnd(20)} ${screen.path}${wrong.length ? `\n      ${wrong.join("\n      ")}` : ""}`);
	if (wrong.length) failed.push(screen.path);
}

await browser.close();
console.log(`${SCREENS.length - failed.length} of ${SCREENS.length} screens as they should be`);
process.exit(failed.length ? 1 : 0);
