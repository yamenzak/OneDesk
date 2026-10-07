// Opens every screen in screens.mjs on the demo workspace, as its person, and
// says which did not show what it should, threw in the browser, or refused.
//
//     ONE_URL=http://onedesk.localhost:8002 ONE_DEMO_PASSWORD=… node tests/browser/run.mjs [path-part]
//
// Playwright is not a dependency of the app: point PLAYWRIGHT_FROM at a
// directory whose node_modules has it, and CHROMIUM at a browser if
// Playwright's own is not installed. ONE_SHOTS names a folder for a
// screenshot of each screen.
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

async function as(who) {
	if (!people.has(who)) {
		const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
		const signed = await context.request.post(`${BASE}/api/method/login`, { form: { usr: who, pwd: PASSWORD } });
		if (!signed.ok()) throw new Error(`${who} could not sign in (${signed.status()})`);
		people.set(who, context);
	}
	return people.get(who);
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
