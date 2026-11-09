const CHECK_PATH = "/api/method/ping";
const TIMEOUT = 15000;
const MISSES = 3;
const STATE = "watch:oneadmin";

async function answering(url) {
	try {
		const answered = await fetch(`${url}${CHECK_PATH}`, { redirect: "manual", signal: AbortSignal.timeout(TIMEOUT) });
		return answered.status === 200;
	} catch {
		return false;
	}
}

function message(env, subject, text) {
	return [
		`From: ${env.SENDER}`,
		`To: ${JSON.parse(env.OPERATORS).join(", ")}`,
		`Subject: ${subject}`,
		"Content-Type: text/plain; charset=utf-8",
		"",
		text,
	].join("\r\n");
}

async function mail(env, subject, text) {
	const sent = await fetch(`https://api.cloudflare.com/client/v4/accounts/${env.ACCOUNT}/email/sending/send_raw`, {
		method: "POST",
		headers: { authorization: `Bearer ${env.MAIL_TOKEN}`, "content-type": "application/json" },
		body: JSON.stringify({ from: env.SENDER, recipients: JSON.parse(env.OPERATORS), mime_message: message(env, subject, text) }),
	});
	if (!sent.ok) throw new Error(`mail was refused: ${sent.status}`);
}

async function checked(env) {
	const held = (await env.SITES.get(STATE, { type: "json" })) || { misses: 0 };
	const up = await answering(env.ADMIN_URL);
	const misses = up ? 0 : held.misses + 1;
	if (misses >= MISSES && !held.told) {
		await mail(env, "OneAdmin is not answering", `${env.ADMIN_URL} missed its last ${MISSES} checks, five minutes apart.`);
		await env.SITES.put(STATE, JSON.stringify({ misses, told: true }));
		return;
	}
	if (up && held.told) {
		await mail(env, "OneAdmin is answering again", `${env.ADMIN_URL} answered its last check.`);
		await env.SITES.put(STATE, JSON.stringify({ misses: 0 }));
		return;
	}
	if (misses !== held.misses) await env.SITES.put(STATE, JSON.stringify({ misses, told: held.told }));
}

export default {
	async scheduled(_controller, env, context) {
		context.waitUntil(checked(env));
	},
	async fetch() {
		return new Response(null, { status: 204 });
	},
};
