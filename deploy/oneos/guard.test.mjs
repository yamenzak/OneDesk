import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import test from "node:test";
import { admission, admitted, cookie, forwarded, route, same, startup, token } from "./guard.js";

const SECRET = "s3cret";
const ID = "sess_0123456789";

test("only the three session paths and the browser path are routed", () => {
	assert.deepEqual(route(`/sessions/${ID}`), { kind: "session", id: ID });
	assert.deepEqual(route(`/sessions/${ID}/stop`), { kind: "stop", id: ID });
	assert.deepEqual(route(`/s/${ID}`), { kind: "browser", id: ID, bare: true });
	assert.deepEqual(route(`/s/${ID}/api/websocket`), { kind: "browser", id: ID, bare: false });
	for (const no of ["/", "/sessions", `/sessions/${ID}/stop/now`, `/sessions/${ID}/start`, "/sessions/short", "/s/../etc", "/s/a%2Fb0000000", "/health"]) assert.equal(route(no), null, no);
});

test("the token is the HMAC of id.expires that OneAdmin makes", async () => {
	const expires = 1900000000;
	const python = createHmac("sha256", SECRET).update(`${ID}.${expires}`).digest("hex");
	assert.equal(await token(SECRET, ID, expires), `${expires}.${python}`);
});

test("a token opens only its own session, only until it expires", async () => {
	const now = 1800000000;
	const given = await token(SECRET, ID, now + 3600);
	assert.equal(await admitted(SECRET, ID, given, now), now + 3600);
	assert.equal(await admitted(SECRET, "sess_another1", given, now), 0, "another session");
	assert.equal(await admitted(SECRET, ID, given, now + 3600), 0, "expired");
	assert.equal(await admitted("other", ID, given, now), 0, "another secret");
	assert.equal(await admitted("", ID, given, now), 0, "no secret set");
	assert.equal(await admitted(SECRET, ID, `${now + 99999}.${given.split(".")[1]}`, now), 0, "a later expiry is not signed");
	for (const bad of [null, "", "abc", `${given}.x`, `-1.${given.split(".")[1]}`]) assert.equal(await admitted(SECRET, ID, bad, now), 0, String(bad));
});

test("the cookie is scoped to the session and lasts as long as the token", () => {
	assert.equal(admission(ID, "9.ab", 1000, 400), `one-os=9.ab; Path=/s/${ID}; Max-Age=600; HttpOnly; Secure; SameSite=Lax`);
	assert.equal(cookie("a=1; one-os=9.ab; b=2"), "9.ab");
	assert.equal(cookie("one-osx=1"), null);
	assert.equal(cookie(null), null);
});

test("the secret is compared whole", () => {
	assert.ok(same("abc", "abc"));
	assert.ok(!same("abc", "abd") && !same("abc", "ab") && !same("", "a") && !same(undefined, "a"));
});

test("a session starts only with https addresses, a known app and size, and a length", () => {
	const good = { file_url: "https://w.example/f", save_url: "https://w.example/s", name: "Budget.xlsx", app: "libreoffice", size: "standard-1", lasts_seconds: 28800 };
	const asked = startup(ID, good);
	assert.equal(asked.lasts, 28800);
	assert.deepEqual(asked.envVars, { ONE_FILE_URL: good.file_url, ONE_SAVE_URL: good.save_url, ONE_FILE_NAME: "Budget.xlsx", ONE_APP: "libreoffice", SUBFOLDER: `/s/${ID}/`, TITLE: "Budget.xlsx" });
	for (const change of [{ file_url: "http://w.example/f" }, { save_url: "" }, { name: "" }, { app: "autocad" }, { size: "standard-4" }, { lasts_seconds: 10 }, { lasts_seconds: "8h" }]) {
		assert.ok(startup(ID, { ...good, ...change }).refused, JSON.stringify(change));
	}
	assert.ok(startup(ID, null).refused);
});

test("what reaches the container carries neither the token nor the secret", () => {
	const request = new Request(`https://os.example/s/${ID}/api?t=1.ab&x=1`, { headers: { cookie: "one-os=1.ab", "x-one-secret": "s", upgrade: "websocket" } });
	const sent = forwarded(request, new URL(request.url));
	assert.equal(sent.url, `https://os.example/s/${ID}/api?x=1`);
	assert.equal(sent.headers.get("cookie"), null);
	assert.equal(sent.headers.get("x-one-secret"), null);
	assert.equal(sent.headers.get("upgrade"), "websocket");
});
