import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { deflateRawSync, gzipSync } from "node:zlib";

import { LIMITS, allowed, inspect, see, sniff } from "./look.js";

function zip(files, { encrypted = false } = {}) {
	const locals = [];
	const centrals = [];
	let offset = 0;
	for (const [name, content] of files) {
		const raw = Buffer.from(content);
		const packed = deflateRawSync(raw);
		const named = Buffer.from(name);
		const local = Buffer.alloc(30);
		local.writeUInt32LE(0x04034b50, 0);
		local.writeUInt16LE(encrypted ? 1 : 0, 6);
		local.writeUInt16LE(8, 8);
		local.writeUInt32LE(packed.length, 18);
		local.writeUInt32LE(raw.length, 22);
		local.writeUInt16LE(named.length, 26);
		const central = Buffer.alloc(46);
		central.writeUInt32LE(0x02014b50, 0);
		central.writeUInt16LE(encrypted ? 1 : 0, 8);
		central.writeUInt16LE(8, 10);
		central.writeUInt32LE(packed.length, 20);
		central.writeUInt32LE(raw.length, 24);
		central.writeUInt16LE(named.length, 28);
		central.writeUInt32LE(offset, 42);
		locals.push(local, named, packed);
		centrals.push(central, named);
		offset += local.length + named.length + packed.length;
	}
	const directory = Buffer.concat(centrals);
	const end = Buffer.alloc(22);
	end.writeUInt32LE(0x06054b50, 0);
	end.writeUInt16LE(files.length, 8);
	end.writeUInt16LE(files.length, 10);
	end.writeUInt32LE(directory.length, 12);
	end.writeUInt32LE(offset, 16);
	return new Uint8Array(Buffer.concat([...locals, directory, end]));
}

function tar(files) {
	const parts = [];
	for (const [name, content] of files) {
		const head = Buffer.alloc(512);
		head.write(name, 0);
		head.write(Buffer.from(content).length.toString(8).padStart(11, "0"), 124);
		head.write("0", 156);
		head.write("ustar", 257);
		const body = Buffer.alloc(Math.ceil(Buffer.from(content).length / 512) * 512);
		Buffer.from(content).copy(body);
		parts.push(head, body);
	}
	return Buffer.concat([...parts, Buffer.alloc(1024)]);
}

const PROGRAM = Buffer.concat([Buffer.from("MZ"), Buffer.alloc(64)]);

function sample(stem, file) {
	const mail = readFileSync(new URL(`../../tests/samples/intake/one_mail/${stem}.eml`, import.meta.url), "utf8");
	const part = mail.split(`filename="${file}"`)[1];
	return new Uint8Array(Buffer.from(part.split("\n\n")[1].split("\n--")[0].replace(/\s+/g, ""), "base64"));
}

test("a file's type is read from what it holds, not its name", () => {
	assert.equal(sniff(PROGRAM), "program");
	assert.equal(sniff(Buffer.from("%PDF-1.7")), "pdf");
	assert.equal(sniff(Buffer.from("Dear Layla,\nthe schedule.")), "text");
	assert.equal(sniff(Buffer.from("  <!DOCTYPE html><form>")), "page");
	assert.equal(sniff(Buffer.from([0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1])), "ole");
});

test("the sample's workbook is Office, holds macros and can be made clean", async () => {
	const said = await inspect("Delivery Schedule November.xlsm", sample("macro-attachment", "Delivery Schedule November.xlsm"));
	assert.equal(said.kind, "ooxml");
	assert.equal(said.macros, "Delivery Schedule November.xlsm");
	assert.equal(said.office, true);
	assert.equal(said.ending, "xlsm");
	assert.equal(said.program, null);
	assert.equal(said.unchecked, null);
	assert.deepEqual(said.inside, [], "an Office file's parts are not listed as an archive's");
});

test("a program in a zip is found by what it is, whatever it is called", async () => {
	const said = await inspect("invoices.zip", zip([["Invoice 114.pdf", "%PDF-1.4"], ["scan/Invoice 115.pdf.exe", PROGRAM]]));
	assert.equal(said.kind, "zip");
	assert.equal(said.program, "scan/Invoice 115.pdf.exe");
	assert.equal(said.office, false);
	assert.deepEqual(said.inside.map((one) => [one.path, one.kind]), [["Invoice 114.pdf", "pdf"], ["scan/Invoice 115.pdf.exe", "program"]]);
});

test("a script is a program by the endings the workspace names", async () => {
	const said = await inspect("photos.tar.gz", new Uint8Array(gzipSync(tar([["photos/view.js", "WScript.Shell"]]))), ["js", "exe"]);
	assert.equal(said.kind, "gzip");
	assert.equal(said.program, "photos.tar/photos/view.js");
});

test("a name that lies about its content says so", async () => {
	const said = await inspect("Invoice.pdf", zip([["a.txt", "hello"]]));
	assert.equal(said.mismatch, true);
	assert.equal((await inspect("Invoice.pdf", Buffer.from("%PDF-1.4"))).mismatch, false);
});

test("archives inside archives stop at the depth limit", async () => {
	let held = zip([["deep.txt", "x"]]);
	for (let i = 0; i < LIMITS.depth + 1; i++) held = zip([[`level${i}.zip`, held]]);
	const said = await inspect("nested.zip", held);
	assert.equal(said.unchecked, "too_deep");
	assert.equal(said.office, false);
});

test("an archive that unpacks too big stops, and one with a password is not opened", async () => {
	const bomb = await inspect("bomb.zip", zip([["zeros.bin", Buffer.alloc(LIMITS.entry + 1)]]));
	assert.equal(bomb.unchecked, "too_big");
	const locked = await inspect("locked.zip", zip([["a.txt", "secret"]], { encrypted: true }));
	assert.equal(locked.unchecked, "encrypted");
});

test("a PDF that runs scripts and an old Office file with macros are named", async () => {
	assert.equal((await inspect("form.pdf", Buffer.from("%PDF-1.4 /OpenAction << /S /JavaScript >>"))).scripts, true);
	const old = Buffer.concat([Buffer.from([0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1]), Buffer.from("_\0V\0B\0A\0_\0P\0R\0O\0J\0E\0C\0T\0")]);
	const said = await inspect("Order.doc", old);
	assert.equal(said.macros, "Order.doc");
	assert.equal(said.office, true);
});

test("only a web address with no sign-in in it is opened", () => {
	assert.equal(allowed("https://online.emiratesnbd.com/login"), true);
	assert.equal(allowed("http://203.0.113.45/enbd/login"), true);
	assert.equal(allowed("javascript:alert(1)"), false);
	assert.equal(allowed("file:///etc/passwd"), false);
	assert.equal(allowed("https://user:pass@example.com/"), false);
});

function browser({ chain = [], final = "https://evil.example/login", password = true, fails = null, hangs = false } = {}) {
	const state = { closed: false };
	const frame = { $: async () => (password ? {} : null) };
	const page = {
		setViewport: async () => {},
		goto: async () => {
			if (hangs) return new Promise(() => {});
			if (fails) throw new Error(fails);
			return { status: () => 200, request: () => ({ redirectChain: () => chain.map((one) => ({ url: () => one })) }) };
		},
		url: () => final,
		title: async () => "Sign in",
		frames: () => [frame],
		screenshot: async () => "AAAA",
	};
	state.open = async () => ({ newPage: async () => page, close: async () => (state.closed = true) });
	return state;
}

test("a link is opened in a browser of its own: where it ends, its redirects, a password asked, a picture", async () => {
	const held = browser({ chain: ["http://203.0.113.45/enbd/login", "https://evil.example/go"] });
	const said = await see(held.open, "http://203.0.113.45/enbd/login", { ...LIMITS, settle: 0 });
	assert.equal(said.final_url, "https://evil.example/login");
	assert.deepEqual(said.redirects, ["http://203.0.113.45/enbd/login", "https://evil.example/go"]);
	assert.equal(said.asks_password, true);
	assert.equal(said.picture, "AAAA");
	assert.equal(said.failed, null);
	assert.equal(held.closed, true, "the browser is thrown away");
});

test("a link that downloads, fails or hangs says so, and the browser is still thrown away", async () => {
	const download = browser({ fails: "net::ERR_ABORTED at https://x.example/a.exe" });
	assert.equal((await see(download.open, "https://x.example/a.exe", { ...LIMITS, settle: 0 })).failed, "download");
	const gone = browser({ fails: "net::ERR_NAME_NOT_RESOLVED" });
	const said = await see(gone.open, "https://nowhere.example/", { ...LIMITS, settle: 0 });
	assert.equal(said.failed, "unreachable");
	assert.equal(said.picture, null);
	const slow = browser({ hangs: true });
	assert.equal((await see(slow.open, "https://slow.example/", { ...LIMITS, settle: 0, most: 50 })).failed, "slow");
	assert.equal(slow.closed && gone.closed && download.closed, true);
});
