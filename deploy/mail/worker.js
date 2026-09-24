/**
 * Mail for m.4dl.app: every message to a workspace's address arrives here.
 *
 * Cloudflare's Email Routing hands the zone's catch-all to this Worker. The
 * addresses are `<slug>@m.4dl.app` for a workspace and `<name>.<slug>@m.4dl.app`
 * for a person in it; a slug has no dot, so the part after the last dot of the
 * local part is always the workspace. Anything else — another subdomain, the
 * apex, a workspace that does not exist, a name that workspace does not have —
 * is refused while the sender's server is still connected, so it bounces rather
 * than vanishing.
 *
 * **Stored first, then told.** The raw message goes to R2 under the workspace's
 * own prefix, beside its files, before anybody is told anything. Only then does
 * a small notice go to the site, signed with the workspace's own secret over
 * the notice's exact bytes. A site that is down, or migrating, misses the
 * notice and loses nothing: it sweeps its prefix for anything it has not read
 * (one_mail/inbound.py). The notice is a hint to be quick, not the delivery.
 *
 * Which site, which bucket and which secret is the workspace's KV record
 * `mail:<slug>`, written by the admin site as the workspace is provisioned and
 * whenever its addresses change — the same namespace the web router reads.
 */

/** A minute: a new address works within one. */
const REMEMBER_FOR = 60;

/** A slug as the admin site makes them. */
const SLUG = /^[a-z0-9][a-z0-9-]{1,39}$/;

export default {
	async email(message, env, ctx) {
		const [local = "", host = ""] = message.to.toLowerCase().split("@");
		if (host !== env.MAIL_DOMAIN) return message.setReject("No such address.");

		const bare = local.split("+")[0];
		const slug = bare.slice(bare.lastIndexOf(".") + 1);
		if (!SLUG.test(slug)) return message.setReject("No such address.");

		const box = await env.SITES.get(`mail:${slug}`, { type: "json", cacheTtl: REMEMBER_FOR });
		if (!box || (Array.isArray(box.names) && !box.names.includes(bare))) {
			return message.setReject("No such address.");
		}

		const bytes = await new Response(message.raw).arrayBuffer();
		// Sortable by arrival, so a sweep can ask for everything after the last
		// one it read; the UUID keeps two in the same millisecond apart.
		const stamp = new Date().toISOString().replace(/[^0-9]/g, "").slice(0, 17);
		const key = `${box.prefix}mail/in/${stamp}-${crypto.randomUUID()}.eml`;
		const bucket = box.bucket === "EU" ? env.FILES_EU : env.FILES;
		await bucket.put(key, bytes, {
			httpMetadata: { contentType: "message/rfc822" },
			customMetadata: { to: message.to, from: message.from },
		});

		const notice = JSON.stringify({ key, to: message.to, from: message.from, size: bytes.byteLength });
		const at = String(Math.floor(Date.now() / 1000));
		const signature = await sign(box.secret, `${at}.${notice}`);
		ctx.waitUntil(
			fetch(`https://${box.site}/api/method/onedesk.one_mail.inbound.notice`, {
				method: "POST",
				headers: { "content-type": "application/json", "x-one-timestamp": at, "x-one-signature": signature },
				body: notice,
			}).catch(() => null)
		);
	},
};

async function sign(secret, text) {
	const key = await crypto.subtle.importKey(
		"raw",
		new TextEncoder().encode(secret),
		{ name: "HMAC", hash: "SHA-256" },
		false,
		["sign"]
	);
	const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(text));
	return [...new Uint8Array(mac)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
