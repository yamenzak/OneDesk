import assert from "node:assert/strict";
import test from "node:test";
import { mint, secretFor, verify } from "./token.ts";

const NOW = 1_800_000_000;

test("a token opens only its own workspace, way, body and minute", async () => {
	const secret = await secretFor("master", "acme");
	const token = await mint(secret, { aud: "workspace", ws: "acme", agent: "one_book", tool: "draft_purchase_invoice" }, "{}", NOW);
	const claims = await verify(secret, token, "workspace", "{}", NOW + 30);
	assert.equal(claims?.agent, "one_book");
	assert.equal(await verify(secret, token, "agents", "{}", NOW), null);
	assert.equal(await verify(secret, token, "workspace", '{"more":1}', NOW), null);
	assert.equal(await verify(secret, token, "workspace", "{}", NOW + 61), null);
	assert.equal(await verify(await secretFor("master", "other"), token, "workspace", "{}", NOW), null);
	assert.equal(await verify(secret, `${token.split(".")[0]}.00`, "workspace", "{}", NOW), null);
});

test("a token lasts two minutes at most", async () => {
	const secret = await secretFor("master", "acme");
	const token = await mint(secret, { aud: "agents", ws: "acme", agent: "one_mail" }, "", NOW, 3600);
	assert.equal(await verify(secret, token, "agents", "", NOW + 121), null);
});

