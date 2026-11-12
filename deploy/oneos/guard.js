export const COOKIE = "one-os";
export const SIZES = ["standard-1"];
export const APPS = ["libreoffice"];
const ID = /^[A-Za-z0-9_-]{8,64}$/;
const encoder = new TextEncoder();

export function same(a, b) {
	if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
	let differ = 0;
	for (let at = 0; at < a.length; at++) differ |= a.charCodeAt(at) ^ b.charCodeAt(at);
	return differ === 0;
}

export function route(pathname) {
	const parts = pathname.split("/");
	if (parts[1] === "sessions" && ID.test(parts[2] || "")) {
		if (parts.length === 3) return { kind: "session", id: parts[2] };
		if (parts.length === 4 && parts[3] === "stop") return { kind: "stop", id: parts[2] };
		return null;
	}
	if (parts[1] === "s" && ID.test(parts[2] || "")) return { kind: "browser", id: parts[2], bare: parts.length === 3 };
	return null;
}

export async function signature(secret, id, expires) {
	const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
	const signed = await crypto.subtle.sign("HMAC", key, encoder.encode(`${id}.${expires}`));
	return [...new Uint8Array(signed)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function token(secret, id, expires) {
	return `${expires}.${await signature(secret, id, expires)}`;
}

export async function admitted(secret, id, given, now = Date.now() / 1000) {
	if (!secret || typeof given !== "string") return 0;
	const [expires, signed, extra] = given.split(".");
	const until = Number(expires);
	if (extra !== undefined || !/^\d{1,12}$/.test(expires || "") || until <= now) return 0;
	return same(signed, await signature(secret, id, expires)) ? until : 0;
}

export function cookie(header) {
	for (const one of (header || "").split(";")) {
		const [name, ...value] = one.trim().split("=");
		if (name === COOKIE) return value.join("=");
	}
	return null;
}

export function admission(id, given, until, now = Date.now() / 1000) {
	const lasts = Math.max(0, Math.floor(until - now));
	return `${COOKIE}=${given}; Path=/s/${id}; Max-Age=${lasts}; HttpOnly; Secure; SameSite=Lax`;
}

export function startup(id, body) {
	const { file_url, save_url, name, app = "libreoffice", size = "standard-1", lasts_seconds } = body || {};
	const lasts = Number(lasts_seconds);
	if (!/^https:\/\//.test(file_url || "") || !/^https:\/\//.test(save_url || "")) return { refused: "file_url and save_url must be https addresses" };
	if (typeof name !== "string" || !name.trim() || name.length > 255) return { refused: "name is missing" };
	if (!APPS.includes(app)) return { refused: `app must be one of ${APPS.join(", ")}` };
	if (!SIZES.includes(size)) return { refused: `size must be one of ${SIZES.join(", ")}` };
	if (!Number.isInteger(lasts) || lasts < 60 || lasts > 86400) return { refused: "lasts_seconds must be between 60 and 86400" };
	return {
		lasts,
		envVars: {
			ONE_FILE_URL: file_url,
			ONE_SAVE_URL: save_url,
			ONE_FILE_NAME: name,
			ONE_APP: app,
			SUBFOLDER: `/s/${id}/`,
			TITLE: name,
		},
	};
}

export function forwarded(request, url) {
	const headers = new Headers(request.headers);
	headers.delete("cookie");
	headers.delete("x-one-secret");
	url.searchParams.delete("t");
	return new Request(url.toString(), { method: request.method, headers, body: request.body, redirect: "manual" });
}
