import { Container, getContainer } from "@cloudflare/containers";
import { admission, admitted, cookie, forwarded, route, same, startup } from "./guard.js";

const PAGE = 3000;
const STATE = 3100;
const GRACE = 600;
const RUNNING = ["running", "healthy"];

function json(body, status = 200) {
	return Response.json(body, { status, headers: { "cache-control": "no-store" } });
}

function page(text, status) {
	return new Response(text, { status, headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" } });
}

export class Session extends Container {
	defaultPort = PAGE;
	requiredPorts = [PAGE, STATE];
	sleepAfter = "10m";
	enableInternet = true;

	async begin(id, body) {
		const asked = startup(id, body);
		if (asked.refused) return { refused: asked.refused };
		const now = await this.getState();
		if (RUNNING.includes(now.status)) return this.status();
		await this.ctx.storage.put({ began: Date.now(), saved_at: null, stopped: false });
		await this.schedule(asked.lasts + GRACE, "expire");
		this.ctx.waitUntil(this.startAndWaitForPorts({ ports: [PAGE, STATE], startOptions: { envVars: asked.envVars } }).catch(() => this.ctx.storage.put("stopped", true)));
		return { state: "starting" };
	}

	async status() {
		const now = await this.getState();
		const kept = await this.ctx.storage.get(["saved_at", "stopped", "began"]);
		if (!RUNNING.includes(now.status)) return { state: kept.get("began") && !kept.get("stopped") && now.status !== "stopped_with_code" ? "starting" : "stopped", idle_seconds: null, saved_at: kept.get("saved_at") || null };
		if (now.status !== "healthy") return { state: "starting", idle_seconds: null, saved_at: kept.get("saved_at") || null };
		const told = await this.told("GET");
		if (!told) return { state: "starting", idle_seconds: null, saved_at: kept.get("saved_at") || null };
		if (told.failed) return { ...(await this.end()), idle_seconds: null, reason: told.failed };
		if (told.saved_at) await this.ctx.storage.put("saved_at", told.saved_at);
		return { state: told.ready ? "running" : "starting", idle_seconds: told.idle_seconds ?? null, saved_at: told.saved_at || kept.get("saved_at") || null };
	}

	async end() {
		const now = await this.getState();
		let saved = (await this.ctx.storage.get("saved_at")) || null;
		if (now.status === "healthy") {
			const told = await this.told("POST");
			if (told?.saved_at) saved = told.saved_at;
		}
		await this.ctx.storage.put({ saved_at: saved, stopped: true });
		if (RUNNING.includes(now.status) || now.status === "stopping") await this.destroy();
		return { state: "stopped", saved_at: saved };
	}

	async expire() {
		await this.end();
	}

	async told(method) {
		try {
			const answered = await this.containerFetch("http://one/state", { method, signal: AbortSignal.timeout(method === "POST" ? 45000 : 5000) }, STATE);
			return answered.ok ? await answered.json() : null;
		} catch {
			return null;
		}
	}

	async fetch(request) {
		const now = await this.getState();
		if (now.status !== "healthy") return page(RUNNING.includes(now.status) ? "OneOS is starting. Try again in a moment." : "This OneOS session has ended.", RUNNING.includes(now.status) ? 503 : 410);
		return this.containerFetch(request, PAGE);
	}
}

async function sessions(request, env, found) {
	if (!env.ONE_SECRET || !same(request.headers.get("x-one-secret") || "", env.ONE_SECRET)) return page("Forbidden", 403);
	const session = getContainer(env.OS, found.id);
	if (found.kind === "stop") return request.method === "POST" ? json(await session.end()) : page("Method Not Allowed", 405);
	if (request.method === "GET") return json(await session.status());
	if (request.method !== "POST") return page("Method Not Allowed", 405);
	let body;
	try {
		body = await request.json();
	} catch {
		return json({ refused: "the body must be JSON" }, 400);
	}
	const began = await session.begin(found.id, body);
	return json(began, began.refused ? 400 : 202);
}

async function browser(request, env, found, url) {
	const given = url.searchParams.get("t");
	if (given) {
		const until = await admitted(env.ONE_SECRET, found.id, given);
		if (!until) return page("This link has expired. Open the file in OneOS again.", 403);
		url.searchParams.delete("t");
		const to = found.bare ? `/s/${found.id}/` : url.pathname;
		return new Response(null, { status: 302, headers: { location: `${to}${url.search}`, "set-cookie": admission(found.id, given, until), "cache-control": "no-store" } });
	}
	if (!(await admitted(env.ONE_SECRET, found.id, cookie(request.headers.get("cookie"))))) return page("Open the file in OneOS from One to see it here.", 403);
	if (found.bare) return new Response(null, { status: 302, headers: { location: `/s/${found.id}/${url.search}` } });
	return getContainer(env.OS, found.id).fetch(forwarded(request, url));
}

export default {
	async fetch(request, env) {
		const url = new URL(request.url);
		const found = route(url.pathname);
		if (!found) return page("Not Found", 404);
		if (found.kind === "browser") return browser(request, env, found, url);
		return sessions(request, env, found);
	},
};
