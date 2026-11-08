const DAY = 24 * 60 * 60;
const SEARCH = /^tenants\/[a-z0-9][a-z0-9-]{0,62}\/search\/$/;
const KEY = /^[A-Za-z0-9._\/-]{1,500}$/;
const MOST_LISTED = 1000;

const answer = (body, status = 200) =>
	new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

function bucketOf(env, which) {
	if (which === "backups") return env.BACKUPS;
	if (which === "files") return env.FILES;
	if (which === "files_eu") return env.FILES_EU;
	return null;
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
	got.body.pipeTo(writable);
	return keep(env, key, readable);
}

async function copied(env, { bucket, prefix, cursor, into }) {
	const source = bucketOf(env, bucket);
	if (!source || bucket === "backups" || !prefix || !into || !KEY.test(into)) return answer({ error: "bad copy" }, 400);
	const listed = await source.list({ prefix, cursor, limit: 200 });
	let copiedCount = 0;
	for (const one of listed.objects) {
		const target = `${into}${one.key}`;
		if (await env.BACKUPS.head(target)) continue;
		const object = await source.get(one.key);
		if (!object) continue;
		const { readable, writable } = new FixedLengthStream(object.size);
		object.body.pipeTo(writable);
		await env.BACKUPS.put(target, readable);
		copiedCount += 1;
	}
	return answer({ copied: copiedCount, cursor: listed.truncated ? listed.cursor : null });
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
		if (!env.ONE_SECRET || request.headers.get("x-one-secret") !== env.ONE_SECRET) return new Response("Forbidden", { status: 403 });
		const url = new URL(request.url);
		const path = decodeURIComponent(url.pathname);
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
		if (path === "/search-credentials") return credentials(env, body);
		return answer({ error: "not found" }, 404);
	},
};
