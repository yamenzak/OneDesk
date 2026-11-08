const DAY = 24 * 60 * 60;
const SEARCH = /^tenants\/[a-z0-9][a-z0-9-]{0,62}\/search\/$/;
const KEY = /^[A-Za-z0-9._\/-]{1,500}$/;
const MOST_LISTED = 1000;
const SLUG = /^[a-z0-9][a-z0-9-]{1,39}$/;
const PART = /^(database|public|private|config)$/;
const FRESH = 10 * 60;
const KEPT_AGAIN = /^(archived|monthly)$/;

const answer = (body, status = 200) =>
	new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

function bucketOf(env, which) {
	if (which === "backups") return env.BACKUPS;
	if (which === "files") return env.FILES;
	if (which === "files_eu") return env.FILES_EU;
	return null;
}

async function moved(object, target, env) {
	const { readable, writable } = new FixedLengthStream(object.size);
	const piped = object.body.pipeTo(writable);
	await env.BACKUPS.put(target, readable);
	await piped;
}

async function keep(env, key, body) {
	if (!KEY.test(key) || key.includes("..")) return answer({ error: "bad key" }, 400);
	if (await env.BACKUPS.head(key)) return answer({ kept: key, already: true });
	await env.BACKUPS.put(key, body);
	return answer({ kept: key });
}

async function fetched(env, { url, key }) {
	if (!url || !url.startsWith("https://")) return answer({ error: "bad url" }, 400);
	if (await env.BACKUPS.head(key || "")) return answer({ kept: key, already: true });
	const got = await fetch(url);
	if (!got.ok || !got.body) return answer({ error: `source answered ${got.status}` }, 502);
	const length = Number(got.headers.get("content-length"));
	if (!length) return answer({ error: "source gave no length" }, 502);
	const { readable, writable } = new FixedLengthStream(length);
	const piped = got.body.pipeTo(writable);
	const said = await keep(env, key, readable);
	await piped;
	return said;
}

async function copied(env, { bucket, prefix, cursor, into }) {
	const source = bucketOf(env, bucket);
	if (!source || bucket === "backups" || !prefix || !into || !KEY.test(into)) return answer({ error: "bad copy" }, 400);
	const listed = await source.list({ prefix, cursor: cursor || undefined, limit: 200 });
	let copiedCount = 0;
	for (const one of listed.objects) {
		const target = `${into}${one.key}`;
		if (await env.BACKUPS.head(target)) continue;
		const object = await source.get(one.key);
		if (!object) continue;
		await moved(object, target, env);
		copiedCount += 1;
	}
	return answer({ copied: copiedCount, cursor: listed.truncated ? listed.cursor : null });
}

async function signature(secret, text) {
	const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
	const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(text));
	return [...new Uint8Array(mac)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function fromWorkspace(request, env, slug, part, name) {
	if (!SLUG.test(slug) || !PART.test(part) || !KEY.test(name) || name.includes("/")) return answer({ error: "bad path" }, 400);
	const held = await env.SITES.get(`backup:${slug}`, { type: "json" });
	const at = Number(request.headers.get("x-one-timestamp"));
	if (!held || !held.secret || !at || Math.abs(Date.now() / 1000 - at) > FRESH) return new Response("Forbidden", { status: 403 });
	const wanted = await signature(held.secret, `${at}.${slug}/${part}/${name}`);
	if (wanted !== request.headers.get("x-one-signature")) return new Response("Forbidden", { status: 403 });
	const day = new Date().toISOString().slice(0, 10);
	const said = await keep(env, `daily/${slug}/${day}/${part}/${name}`, request.body);
	if (day.endsWith("-01")) await again(env, { slug, day, into: "monthly" });
	return said;
}

async function again(env, { slug, day, into }) {
	if (!SLUG.test(slug || "") || !/^\d{4}-\d{2}-\d{2}$/.test(day || "") || !KEPT_AGAIN.test(into || "")) return answer({ error: "bad copy" }, 400);
	const listed = await env.BACKUPS.list({ prefix: `daily/${slug}/${day}/` });
	const kept = [];
	for (const one of listed.objects) {
		const target = one.key.replace(/^daily\//, `${into}/`);
		if (await env.BACKUPS.head(target)) continue;
		const object = await env.BACKUPS.get(one.key);
		if (!object) continue;
		await moved(object, target, env);
		kept.push(target);
	}
	return answer({ kept });
}

async function credentials(env, { bucket, prefix, ttl }) {
	if (!SEARCH.test(prefix || "") || !JSON.parse(env.TENANT_BUCKETS).includes(bucket)) return answer({ error: "bad prefix" }, 400);
	const asked = await fetch(`https://api.cloudflare.com/client/v4/accounts/${env.ACCOUNT}/r2/temp-access-credentials`, {
		method: "POST",
		headers: { authorization: `Bearer ${env.R2_TOKEN}`, "content-type": "application/json", ...(bucket === env.EU_BUCKET ? { "cf-r2-jurisdiction": "eu" } : {}) },
		body: JSON.stringify({ bucket, parentAccessKeyId: env.PARENT_KEY, permission: "object-read-write", prefixes: [prefix], ttlSeconds: Math.min(Number(ttl) || 3600, DAY) }),
	});
	return new Response(asked.body, { status: asked.status, headers: { "content-type": "application/json" } });
}

export default {
	async fetch(request, env) {
		const url = new URL(request.url);
		const path = decodeURIComponent(url.pathname);
		const workspace = path.match(/^\/workspace\/([^/]+)\/([^/]+)\/([^/]+)$/);
		if (workspace && request.method === "PUT") return fromWorkspace(request, env, ...workspace.slice(1));
		if (!env.ONE_SECRET || request.headers.get("x-one-secret") !== env.ONE_SECRET) return new Response("Forbidden", { status: 403 });
		if (path.startsWith("/backup/")) {
			const key = path.slice("/backup/".length);
			if (request.method === "PUT") return keep(env, key, request.body);
			if (request.method === "GET") {
				const object = await env.BACKUPS.get(key);
				return object ? new Response(object.body, { headers: { "content-length": String(object.size) } }) : answer({ error: "not found" }, 404);
			}
			return answer({ error: "never" }, 405);
		}
		if (path === "/backups" && request.method === "GET") {
			const listed = await env.BACKUPS.list({ prefix: url.searchParams.get("prefix") || "", cursor: url.searchParams.get("cursor") || undefined, limit: MOST_LISTED });
			return answer({ objects: listed.objects.map((one) => ({ key: one.key, size: one.size, uploaded: one.uploaded })), cursor: listed.truncated ? listed.cursor : null });
		}
		if (request.method !== "POST") return answer({ error: "never" }, 405);
		const body = await request.json().catch(() => ({}));
		if (path === "/fetch") return fetched(env, body);
		if (path === "/copy") return copied(env, body);
		if (path === "/again") return again(env, body);
		if (path === "/search-credentials") return credentials(env, body);
		return answer({ error: "not found" }, 404);
	},
};
