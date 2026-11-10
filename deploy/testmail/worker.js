export default {
	async email(message, env) {
		if (!(await keep(env, message.to, message.from, message.raw))) message.setReject("No such address.");
	},

	async fetch(request, env) {
		if (request.method !== "POST") return new Response(null, { status: 405 });
		const kept = await keep(env, request.headers.get("x-one-to") || "", request.headers.get("x-one-from") || "", request.body);
		return new Response(null, { status: kept ? 204 : 404 });
	},
};

async function keep(env, to, from, raw) {
	const address = to.trim().toLowerCase();
	if (address.split("@")[1] !== env.TEST_DOMAIN) return false;
	const bytes = await new Response(raw).arrayBuffer();
	const stamp = new Date().toISOString().replace(/[^0-9]/g, "").slice(0, 17);
	await env.MAIL.put(`${address}/${stamp}-${crypto.randomUUID()}.eml`, bytes, {
		httpMetadata: { contentType: "message/rfc822" },
		customMetadata: { to: address, from },
	});
	return true;
}
