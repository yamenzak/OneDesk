/**
 * The signed, short-lived token that carries an agent's call between the
 * Worker and one workspace (README.md, The token). Its Python twin is
 * onedesk/one_ai/agents/token.py; tests/test_agents.py holds them to each other.
 */

export const LONGEST = 120;

export type Claims = {
	aud: "workspace" | "agents";
	ws: string;
	agent: string;
	tool?: string;
	for?: string;
	sum: string;
	iat: number;
	exp: number;
	jti: string;
};

const encoder = new TextEncoder();

function hex(bytes: ArrayBuffer): string {
	return [...new Uint8Array(bytes)].map((one) => one.toString(16).padStart(2, "0")).join("");
}

function base64url(text: string): string {
	return btoa(String.fromCharCode(...encoder.encode(text))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function unbase64url(text: string): string {
	const padded = text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4);
	return new TextDecoder().decode(Uint8Array.from(atob(padded), (one) => one.charCodeAt(0)));
}

export async function hmac(secret: string, text: string): Promise<string> {
	const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
	return hex(await crypto.subtle.sign("HMAC", key, encoder.encode(text)));
}

export async function sum(body: string): Promise<string> {
	return hex(await crypto.subtle.digest("SHA-256", encoder.encode(body)));
}

/** A workspace's own secret, from the Worker's ONE_SECRET and its slug: OneAdmin gives the workspace the same. */
export function secretFor(master: string, workspace: string): Promise<string> {
	return hmac(master, `agents:${workspace}`);
}

export async function mint(secret: string, claims: Omit<Claims, "iat" | "exp" | "jti" | "sum">, body: string, now: number, lasts = 60): Promise<string> {
	const full: Claims = { ...claims, sum: await sum(body), iat: now, exp: now + Math.min(lasts, LONGEST), jti: crypto.randomUUID() };
	const said = base64url(JSON.stringify(full));
	return `${said}.${await hmac(secret, said)}`;
}

function same(one: string, other: string): boolean {
	if (one.length !== other.length) return false;
	let differs = 0;
	for (let at = 0; at < one.length; at++) differs |= one.charCodeAt(at) ^ other.charCodeAt(at);
	return differs === 0;
}

/** The claims of a token this secret signed for `aud`, over this body, still in its time; null for any other. */
export async function verify(secret: string, token: string, aud: Claims["aud"], body: string, now: number): Promise<Claims | null> {
	const [said, signed] = (token || "").split(".");
	if (!said || !signed || !secret || !same(await hmac(secret, said), signed)) return null;
	let claims: Claims;
	try {
		claims = JSON.parse(unbase64url(said));
	} catch {
		return null;
	}
	if (claims.aud !== aud || claims.exp < now || claims.iat > now + 5 || claims.exp - claims.iat > LONGEST) return null;
	if (claims.sum !== (await sum(body))) return null;
	return claims;
}
