import { createRequire } from "node:module";
import { join } from "node:path";

const require = createRequire(join(process.env.PLAYWRIGHT_FROM || process.cwd(), "noop.js"));
const { chromium } = require("playwright");

const BASE = process.env.ONE_URL || "http://onedesk.localhost:8002";
const PASSWORD = process.env.ONE_DEMO_PASSWORD;
const WHO = process.env.ONE_WHO || "wsadmin@one.test";
const ROWS = Number(process.env.ONE_ROWS || 3);
const ONLY = (process.argv[2] || "").toLowerCase();
if (!PASSWORD) throw new Error("Set ONE_DEMO_PASSWORD to the demo people's password.");

const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const signed = await context.request.post(`${BASE}/api/method/login`, { form: { usr: WHO, pwd: PASSWORD } });
if (!signed.ok()) throw new Error(`${WHO} could not sign in (${signed.status()})`);

const settle = (page) => page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {}).then(() => page.waitForTimeout(1200));

const standing = (page) =>
	page.evaluate(() => {
		if (typeof frappe === "undefined" || !frappe.app) return { where: location.pathname + location.search, shell: null, wrong: ["left the desk"] };
		const sidebar = frappe.app?.sidebar;
		const route = frappe.get_route();
		const shell = sidebar?.current_module;
		const entity = sidebar.entity_from_route(route);
		const kind = sidebar.link_type_from_route(route);
		const listed = !!entity && sidebar.get_modules_linking(entity, kind).includes(shell);
		const home = sidebar.canonical_shell_for(route);
		const system = frappe.router.page_info_for(route)?.system_page;
		const rows = [...document.querySelectorAll(".body-sidebar a.item-anchor")].filter((one) => one.offsetParent).length;
		const first = location.pathname.replace(/^\/desk\//, "").split("/")[0];
		const named = frappe.router.shell_routes?.[first];
		const wrong = [];
		if (!system && entity && !listed && home && shell !== home) wrong.push(`${shell}'s rail does not list ${entity}, whose own rail is ${home}`);
		if (!rows) wrong.push(`${shell}'s rail has no rows`);
		if (named && named !== shell) wrong.push(`the address names ${named} in ${shell}`);
		return { where: location.pathname + location.search, shell, wrong };
	});

const failed = [];
const page = await context.newPage();
let here = "Home";
page.on("pageerror", (error) => failed.push(`${here}: threw ${error.message}${error.stack ? " at " + error.stack.split("\n").slice(1, 3).join(" ").trim() : ""}`));
await page.goto(`${BASE}/desk/one`, { waitUntil: "networkidle", timeout: 60000 });
await settle(page);
const apps = await page.evaluate(() => [...document.querySelectorAll(".dock-items .dock-item[aria-label]")].filter((one) => one.offsetParent).map((one) => one.getAttribute("aria-label")));

for (const app of apps.filter((one) => !ONLY || one.toLowerCase().includes(ONLY))) {
	const trail = [];
	here = app;
	const look = async (step) => {
		const now = await standing(page);
		trail.push(`${step}: ${now.where} in ${now.shell}`);
		for (const one of now.wrong) failed.push(`${app}, ${step} (${now.where}): ${one}`);
		return now;
	};
	await page.goto(`${BASE}/desk/one`, { waitUntil: "networkidle", timeout: 60000 });
	await settle(page);
	const home = await look("Home");
	await page.locator(`.dock-items .dock-item[aria-label="${app}"]`).first().click();
	await settle(page);
	const opened = await look("opened");
	const hrefs = await page.evaluate(
		(count) =>
			[...document.querySelectorAll(".body-sidebar a.item-anchor[href^='/desk/']")]
				.filter((one) => one.offsetParent)
				.map((one) => one.getAttribute("href"))
				.filter((href) => href !== location.pathname)
				.slice(0, count),
		ROWS
	);
	let steps = 0;
	for (const href of hrefs) {
		const row = page.locator(`.body-sidebar a.item-anchor[href="${href}"]`).first();
		if (!(await row.isVisible().catch(() => false))) continue;
		await row.click();
		await settle(page);
		steps++;
		await look(`row ${href}`);
	}
	let end = await standing(page);
	for (let back = 1; back <= steps + 2 && end.where !== home.where; back++) {
		await page.goBack();
		await settle(page);
		end = await look(`Back ${back}`);
		if (!end.shell) break;
	}
	if (end.where !== home.where) failed.push(`${app}: Back from ${opened.where} ended at ${end.where}, not ${home.where}`);
	console.log(`${failed.some((one) => one.startsWith(app + ",") || one.startsWith(app + ":")) ? "FAIL" : "ok  "}  ${app}  (${trail.length} steps)`);
}

await browser.close();
if (failed.length) {
	console.log(`\n${failed.length} wrong:\n  ${failed.join("\n  ")}`);
	process.exit(1);
}
console.log(`\nEvery app routes to its own rail and Back returns.`);
