// A clip for Help or What's New: a screen of the demo workspace recorded
// while a few steps are done on it, written as a GIF of at most 9 seconds
// (one/media.py LONGEST_CLIP, the docs skill).
//
//   ONE_DEMO_PASSWORD=… PLAYWRIGHT_FROM=/path/with/playwright node scripts/clip.mjs onedesk/one_mail/help/rules/new-rule.gif \
//     --url /desk/onemail --user huda@one.test --steps steps.json
//
// steps.json is a list, done in order, each one of:
//   {"wait": 800}                         milliseconds
//   {"click": "selector"}                 a click, the pointer moved there first
//   {"type": ["selector", "words"]}       typed a letter at a time
//   {"press": "Enter"}
//   {"eval": "javascript"}                run in the page
// The clip starts once the screen has settled and ends half a second after
// the last step. --width (960) and --fps (10) shape it; --size W,H (1280,800)
// is the window recorded.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";

// Playwright from where it is installed, as tests/browser/run.mjs finds it.
const { chromium } = createRequire(path.join(process.env.PLAYWRIGHT_FROM || process.cwd(), "noop.js"))("playwright");

const LONGEST = 9;
const [out, ...rest] = process.argv.slice(2);
const flag = (name, fallback) => {
	const at = rest.indexOf(`--${name}`);
	return at >= 0 ? rest[at + 1] : fallback;
};
if (!out || !out.endsWith(".gif")) {
	console.error("usage: node scripts/clip.mjs <file.gif> --url /desk/... [--user u] [--steps steps.json] [--width 960] [--fps 10]");
	process.exit(2);
}
const base = process.env.ONE_URL || "http://onedesk.localhost:8002";
const [w, h] = flag("size", "1280,800").split(",").map(Number);
const steps = flag("steps") ? JSON.parse(fs.readFileSync(flag("steps"), "utf8")) : [];
const width = Number(flag("width", 960));
const fps = Number(flag("fps", 10));
const room = fs.mkdtempSync(path.join(os.tmpdir(), "clip-"));

const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
const context = await browser.newContext({ viewport: { width: w, height: h }, recordVideo: { dir: room, size: { width: w, height: h } } });
const page = await context.newPage();
const opened = Date.now();
await page.request.post(`${base}/api/method/login`, { form: { usr: flag("user", "huda@one.test"), pwd: process.env.ONE_DEMO_PASSWORD } });
await page.goto(base + flag("url", "/desk"));
await page.waitForLoadState("networkidle").catch(() => {});
// A first tour would cover the screen.
await page.addStyleTag({ content: "#driver-popover-item,#driver-page-overlay,#driver-highlighted-element-stage{display:none!important}" });
await page.waitForTimeout(800);
const start = (Date.now() - opened) / 1000;
for (const step of steps) {
	if (step.wait) await page.waitForTimeout(step.wait);
	if (step.click) {
		const box = await page.locator(step.click).first().boundingBox();
		if (box) await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 12 });
		await page.locator(step.click).first().click();
	}
	if (step.type) await page.locator(step.type[0]).first().pressSequentially(step.type[1], { delay: 60 });
	if (step.press) await page.keyboard.press(step.press);
	if (step.eval) await page.evaluate(step.eval);
}
await page.waitForTimeout(500);
const length = (Date.now() - opened) / 1000 - start;
const video = await page.video().path();
await context.close();
await browser.close();

if (length > LONGEST) console.warn(`the steps took ${length.toFixed(1)} s; the clip keeps the first ${LONGEST}`);
const keep = Math.min(length, LONGEST).toFixed(2);
const filter = `fps=${fps},scale=${width}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`;
fs.mkdirSync(path.dirname(out), { recursive: true });
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-ss", start.toFixed(2), "-t", keep, "-i", video, "-vf", filter, "-loop", "0", out]);
fs.rmSync(room, { recursive: true, force: true });
console.log(`${out}: ${keep} s, ${(fs.statSync(out).size / 1024).toFixed(0)} KB`);
