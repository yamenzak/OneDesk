import puppeteer from "@cloudflare/puppeteer";
import { Container, getContainer } from "@cloudflare/containers";

import { allowed, inspect, see } from "./look.js";

const CONVERTS = ["/forms/libreoffice/convert", "/forms/pdfengines/merge", "/health"];
const MOST_BYTES = 30 * 1024 * 1024;

export class Office extends Container {
	defaultPort = 3000;
	sleepAfter = "5m";
}

function json(body, status = 200) {
	return Response.json(body, { status, headers: { "cache-control": "no-store" } });
}

async function file(request) {
	const bytes = new Uint8Array(await request.arrayBuffer());
	if (bytes.length > MOST_BYTES) return json({ refused: "too_big" }, 413);
	const name = decodeURIComponent(request.headers.get("x-one-name") || "file");
	const programs = (request.headers.get("x-one-programs") || "").split(",").filter(Boolean);
	return json(await inspect(name, bytes, programs));
}

async function link(request, env) {
	const { url } = await request.json().catch(() => ({}));
	if (!allowed(url)) return json({ refused: "address" }, 400);
	return json(await see(() => puppeteer.launch(env.BROWSER), url));
}

export default {
	async fetch(request, env) {
		const { pathname } = new URL(request.url);
		if (!env.ONE_SECRET || request.headers.get("x-one-secret") !== env.ONE_SECRET) return new Response("Forbidden", { status: 403 });
		if (request.method === "POST" && pathname === "/guard/file") return file(request);
		if (request.method === "POST" && pathname === "/guard/link") return link(request, env);
		if (!CONVERTS.includes(pathname)) return new Response("Not Found", { status: 404 });
		return getContainer(env.OFFICE, "office").fetch(request);
	},
};
