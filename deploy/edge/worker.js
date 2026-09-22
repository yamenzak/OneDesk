/**
 * The edge router: how <slug>.t.4dl.app becomes a Frappe Cloud site.
 *
 * Frappe Cloud serves a site under its own name and holds the certificate for
 * that name. It will not serve ours: a wildcard certificate there needs a Root
 * Domain, which is an operator record with AWS keys, and we are a customer. So
 * the name is never given to press at all. This Worker answers for it, rewrites
 * the Host header to the press site name, and forwards. Press sees a request
 * for a site it already serves and answers it normally.
 *
 * The browser's TLS is Cloudflare's, from the Advanced Certificate Manager
 * wildcard on *.t.4dl.app. The hop to press is TLS too, to a hostname whose
 * certificate press holds. Nothing is unencrypted and no certificate is ours.
 *
 * The slug-to-site map lives in Workers KV, written by the admin site as each
 * workspace is provisioned. It is read here rather than asked for, because the
 * admin site is the control path and must never be in the data path — a Worker
 * that called it on every request would make an admin outage everybody's
 * outage.
 */

/** Long enough that a hot slug costs one KV read a minute, short enough that a
 *  workspace moved between benches is right again quickly. */
const REMEMBER_FOR = 60;

/** Headers a request must not arrive with, because the origin would believe
 *  them. Anybody can send these; only we may set them. */
const STRIPPED = ["x-forwarded-host", "x-one-slug", "x-real-ip"];

export default {
	async fetch(request, env, ctx) {
		const asked = new URL(request.url);
		const slug = asked.hostname.split(".")[0];

		if (!slug || slug === asked.hostname) {
			return new Response("Not found", { status: 404 });
		}

		const site = await env.SITES.get(slug, { cacheTtl: REMEMBER_FOR });
		if (!site) {
			// No workspace by that name. Said plainly rather than passed to press,
			// which would answer with its own "site not found" page and confuse
			// somebody who mistyped a subdomain.
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
		headers.set("Host", site);
		// What the site should believe it is called. Frappe reads host_name from
		// its own config for links, so this is belt and braces rather than the
		// mechanism, but a redirect built from the Host header lands right.
		headers.set("X-Forwarded-Host", asked.hostname);

		const sent = new Request(to, {
			method: request.method,
			headers,
			body: request.body,
			redirect: "manual",
		});

		const answered = await fetch(sent, { cf: { resolveOverride: site } });

		// A redirect press builds from its own name would walk the browser off
		// our domain and onto one whose certificate does not match what the URL
		// bar says. Rewritten back.
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
