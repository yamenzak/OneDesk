
const REMEMBER_FOR = 60;

const SLUG = /^[a-z0-9][a-z0-9-]{1,39}$/;

export default {
	async email(message, env, ctx) {
		const [local = "", host = ""] = message.to.toLowerCase().split("@");
		if (env.TESTMAIL && host === env.TEST_DOMAIN) return toTestMail(message, env);
		if (host !== env.MAIL_DOMAIN) return message.setReject("No such address.");

		const bare = local.split("+")[0];
		const slug = bare.slice(bare.lastIndexOf(".") + 1);
		if (!SLUG.test(slug)) return message.setReject("No such address.");

		const box = await env.SITES.get(`mail:${slug}`, { type: "json", cacheTtl: REMEMBER_FOR });
		if (!box || (Array.isArray(box.names) && !box.names.includes(bare))) {
			return message.setReject("No such address.");
		}

		const bytes = await new Response(message.raw).arrayBuffer();
		const stamp = new Date().toISOString().replace(/[^0-9]/g, "").slice(0, 17);
		const name = `${stamp}-${crypto.randomUUID()}~${bare}.eml`;
		const key = `${box.prefix}mail/in/${name}`;
		const bucket = box.bucket === "EU" ? env.FILES_EU : env.FILES;
		await bucket.put(key, bytes, {
			httpMetadata: { contentType: "message/rfc822" },
			customMetadata: { to: message.to, from: message.from },
		});

		const notice = JSON.stringify({ key: `mail/in/${name}`, to: message.to, from: message.from, size: bytes.byteLength });
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

async function toTestMail(message, env) {
	const handed = await env.TESTMAIL.fetch("https://testmail/", {
		method: "POST",
		headers: { "x-one-to": message.to, "x-one-from": message.from },
		body: await new Response(message.raw).arrayBuffer(),
	});
	if (!handed.ok) message.setReject("No such address.");
}

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
