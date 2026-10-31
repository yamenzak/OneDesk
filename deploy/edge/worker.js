
const REMEMBER_FOR = 60;

const STRIPPED = ["x-forwarded-host", "x-one-slug", "x-real-ip"];

// The weather place's location button asks where it is; only that request
// carries the town Cloudflare places the visitor's internet address in.
const LOCATING = "/api/method/onedesk.one.weather.located";
const LOCATED = {
	"x-one-city": "city",
	"x-one-region": "region",
	"x-one-country": "country",
	"x-one-latitude": "latitude",
	"x-one-longitude": "longitude",
};

export default {
	async fetch(request, env, ctx) {
		const asked = new URL(request.url);
		const host = asked.hostname.toLowerCase();
		const ours = env.TENANT_DOMAIN ? `.${env.TENANT_DOMAIN}` : null;

		let site = null;
		if (ours && host.endsWith(ours)) {
			const slug = host.slice(0, -ours.length);
			if (slug && !slug.includes(".")) site = await env.SITES.get(slug, { cacheTtl: REMEMBER_FOR });
		} else {
			site = await env.SITES.get(`host:${host}`, { cacheTtl: REMEMBER_FOR });
		}
		if (!site) {
			return new Response("No workspace by that name.", {
				status: 404,
				headers: { "content-type": "text/plain; charset=utf-8" },
			});
		}

		const to = new URL(request.url);
		to.hostname = site;
		to.port = "";
		to.protocol = "https:";

		const headers = new Headers(request.headers);
		for (const header of STRIPPED) headers.delete(header);
		for (const [header, key] of Object.entries(LOCATED)) {
			headers.delete(header);
			const value = request.cf && request.cf[key];
			if (asked.pathname === LOCATING && value) headers.set(header, encodeURIComponent(String(value)));
		}
		headers.set("Host", site);
		headers.set("X-Forwarded-Host", asked.hostname);

		const sent = new Request(to, {
			method: request.method,
			headers,
			body: request.body,
			redirect: "manual",
		});

		const answered = await fetch(sent, { cf: { resolveOverride: site } });

		const where = answered.headers.get("location");
		if (!where) return answered;

		let back;
		try {
			back = new URL(where, to);
		} catch {
			return answered;
		}
		if (back.hostname !== site) return answered;

		back.hostname = asked.hostname;
		const fixed = new Headers(answered.headers);
		fixed.set("location", back.toString());
		return new Response(answered.body, {
			status: answered.status,
			statusText: answered.statusText,
			headers: fixed,
		});
	},
};
