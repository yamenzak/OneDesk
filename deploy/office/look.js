export const LIMITS = { depth: 3, entries: 1000, bytes: 64 * 1024 * 1024, entry: 32 * 1024 * 1024, ratio: 200, listed: 100, wait: 15000, settle: 2000, most: 30000 };

const PROGRAM_MAGIC = [
	[0, [0x4d, 0x5a]],
	[0, [0x7f, 0x45, 0x4c, 0x46]],
	[0, [0xfe, 0xed, 0xfa, 0xce]],
	[0, [0xfe, 0xed, 0xfa, 0xcf]],
	[0, [0xce, 0xfa, 0xed, 0xfe]],
	[0, [0xcf, 0xfa, 0xed, 0xfe]],
	[0, [0xca, 0xfe, 0xba, 0xbe]],
	[0, [0x23, 0x21]],
	[0, [0x4c, 0x00, 0x00, 0x00, 0x01, 0x14, 0x02, 0x00]],
	[0, [0x64, 0x65, 0x78, 0x0a]],
	[0x8001, [0x43, 0x44, 0x30, 0x30, 0x31]],
];

const MAGIC = [
	["zip", 0, [0x50, 0x4b, 0x03, 0x04]],
	["zip", 0, [0x50, 0x4b, 0x05, 0x06]],
	["gzip", 0, [0x1f, 0x8b]],
	["tar", 257, [0x75, 0x73, 0x74, 0x61, 0x72]],
	["unopened", 0, [0x52, 0x61, 0x72, 0x21, 0x1a, 0x07]],
	["unopened", 0, [0x37, 0x7a, 0xbc, 0xaf, 0x27, 0x1c]],
	["unopened", 0, [0x4d, 0x53, 0x43, 0x46]],
	["ole", 0, [0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1]],
	["pdf", 0, [0x25, 0x50, 0x44, 0x46]],
	["rtf", 0, [0x7b, 0x5c, 0x72, 0x74, 0x66]],
	["png", 0, [0x89, 0x50, 0x4e, 0x47]],
	["jpeg", 0, [0xff, 0xd8, 0xff]],
	["gif", 0, [0x47, 0x49, 0x46, 0x38]],
	["tiff", 0, [0x49, 0x49, 0x2a, 0x00]],
	["tiff", 0, [0x4d, 0x4d, 0x00, 0x2a]],
];

export const EXPECTED = {
	pdf: ["pdf"], rtf: ["rtf"], png: ["png"], jpg: ["jpeg"], jpeg: ["jpeg"], gif: ["gif"], tif: ["tiff"], tiff: ["tiff"],
	zip: ["zip"], gz: ["gzip"], tgz: ["gzip"], tar: ["tar"], txt: ["text"], csv: ["text"], html: ["page"], htm: ["page"],
	doc: ["ole", "rtf"], xls: ["ole"], ppt: ["ole"], dot: ["ole"], xlt: ["ole"], pps: ["ole"], msg: ["ole"],
	docx: ["ooxml"], docm: ["ooxml"], dotx: ["ooxml"], dotm: ["ooxml"], xlsx: ["ooxml"], xlsm: ["ooxml"], xltx: ["ooxml"],
	xltm: ["ooxml"], xlsb: ["ooxml"], xlam: ["ooxml"], pptx: ["ooxml"], pptm: ["ooxml"], potx: ["ooxml"], potm: ["ooxml"],
	ppsx: ["ooxml"], ppsm: ["ooxml"], odt: ["odf"], ods: ["odf"], odp: ["odf"], odg: ["odf"],
};

const OFFICE = new Set(["ooxml", "odf", "ole", "rtf"]);
const LISTS = new Set(["zip", "tar", "gzip"]);
const ENDINGS = { ooxml: "docx", odf: "odt", ole: "doc", rtf: "rtf" };

class Stop extends Error {
	constructor(why) {
		super(why);
		this.why = why;
	}
}

const at = (bytes, offset, wanted) => bytes.length >= offset + wanted.length && wanted.every((one, i) => bytes[offset + i] === one);
const u16 = (bytes, offset) => bytes[offset] | (bytes[offset + 1] << 8);
const u32 = (bytes, offset) => (bytes[offset] | (bytes[offset + 1] << 8) | (bytes[offset + 2] << 16) | (bytes[offset + 3] << 24)) >>> 0;
const ending = (name) => (String(name || "").includes(".") ? String(name).split(".").pop().trim().toLowerCase() : "");
const text = (bytes) => new TextDecoder("utf-8").decode(bytes);
const latin = (bytes) => new TextDecoder("latin1").decode(bytes);

function holds(bytes, words) {
	const said = latin(bytes);
	return words.some((one) => said.includes(one));
}

const WIDE = (word) => [...word].map((one) => `${one}\0`).join("");

export function sniff(bytes) {
	if (PROGRAM_MAGIC.some(([offset, wanted]) => at(bytes, offset, wanted))) return "program";
	const found = MAGIC.find(([, offset, wanted]) => at(bytes, offset, wanted));
	if (found) return found[0];
	if (at(bytes, 0, [0x52, 0x49, 0x46, 0x46]) && at(bytes, 8, [0x57, 0x45, 0x42, 0x50])) return "webp";
	const head = bytes.subarray(0, 512);
	const opening = latin(head).replace(/^﻿|^ï»¿/, "").trimStart().toLowerCase();
	if (opening.startsWith("<!doctype html") || opening.startsWith("<html") || opening.startsWith("<svg") || opening.startsWith("<script")) return "page";
	if (head.length && head.every((one) => one === 9 || one === 10 || one === 13 || one >= 32)) return "text";
	return "unknown";
}

function central(bytes) {
	const from = Math.max(0, bytes.length - 65557);
	let end = -1;
	for (let i = bytes.length - 22; i >= from; i--) {
		if (u32(bytes, i) === 0x06054b50) {
			end = i;
			break;
		}
	}
	if (end < 0) throw new Stop("unreadable");
	const count = u16(bytes, end + 10);
	let offset = u32(bytes, end + 16);
	if (count === 0xffff || offset === 0xffffffff) throw new Stop("unreadable");
	if (count > LIMITS.entries) throw new Stop("too_many");
	const entries = [];
	for (let i = 0; i < count; i++) {
		if (u32(bytes, offset) !== 0x02014b50) throw new Stop("unreadable");
		const named = u16(bytes, offset + 28);
		const extra = u16(bytes, offset + 30);
		const comment = u16(bytes, offset + 32);
		entries.push({
			flags: u16(bytes, offset + 8),
			method: u16(bytes, offset + 10),
			packed: u32(bytes, offset + 20),
			size: u32(bytes, offset + 24),
			local: u32(bytes, offset + 42),
			name: text(bytes.subarray(offset + 46, offset + 46 + named)),
		});
		offset += 46 + named + extra + comment;
	}
	return entries;
}

export function zipKind(names) {
	const lowered = names.map((one) => one.toLowerCase());
	if (lowered.includes("[content_types].xml")) return "ooxml";
	if (lowered.includes("mimetype") && lowered.some((one) => one.startsWith("meta-inf/manifest.xml"))) return "odf";
	if (lowered.includes("meta-inf/manifest.mf") && lowered.some((one) => one.endsWith(".class"))) return "program";
	if (lowered.includes("androidmanifest.xml") || lowered.includes("classes.dex") || lowered.includes("appxmanifest.xml")) return "program";
	return "zip";
}

async function inflated(packed, format, cap, state) {
	const reader = new Blob([packed]).stream().pipeThrough(new DecompressionStream(format)).getReader();
	const parts = [];
	let size = 0;
	for (;;) {
		const { done, value } = await reader.read();
		if (done) break;
		size += value.length;
		state.bytes += value.length;
		if (size > cap || state.bytes > LIMITS.bytes) {
			await reader.cancel().catch(() => {});
			throw new Stop("too_big");
		}
		parts.push(value);
	}
	const out = new Uint8Array(size);
	let offset = 0;
	for (const one of parts) {
		out.set(one, offset);
		offset += one.length;
	}
	return out;
}

async function entryOf(bytes, entry, state) {
	if (entry.flags & 1) throw new Stop("encrypted");
	if (entry.size > LIMITS.entry) throw new Stop("too_big");
	if (entry.packed && entry.size / entry.packed > LIMITS.ratio && entry.size > 1024 * 1024) throw new Stop("too_big");
	if (u32(bytes, entry.local) !== 0x04034b50) throw new Stop("unreadable");
	const start = entry.local + 30 + u16(bytes, entry.local + 26) + u16(bytes, entry.local + 28);
	const packed = bytes.subarray(start, start + entry.packed);
	if (entry.method === 0) {
		state.bytes += packed.length;
		if (state.bytes > LIMITS.bytes) throw new Stop("too_big");
		return packed;
	}
	if (entry.method === 8) return inflated(packed, "deflate-raw", LIMITS.entry, state);
	throw new Stop("unreadable");
}

function tarEntries(bytes) {
	const entries = [];
	let offset = 0;
	while (offset + 512 <= bytes.length) {
		const head = bytes.subarray(offset, offset + 512);
		if (head.every((one) => one === 0)) break;
		const name = text(head.subarray(0, 100)).replace(/\0.*$/s, "");
		const prefix = text(head.subarray(345, 500)).replace(/\0.*$/s, "");
		const size = parseInt(text(head.subarray(124, 136)).replace(/\0.*$/s, "").trim() || "0", 8) || 0;
		const type = String.fromCharCode(head[156] || 48);
		if (type === "0" || type === "7") entries.push({ name: prefix ? `${prefix}/${name}` : name, data: bytes.subarray(offset + 512, offset + 512 + size) });
		offset += 512 + Math.ceil(size / 512) * 512;
		if (entries.length > LIMITS.entries) throw new Stop("too_many");
	}
	return entries;
}

function leaf(path, kind, bytes, state, programs) {
	if (kind === "program" || programs.has(ending(path))) state.program ??= path;
	if (kind === "ole" && holds(bytes, ["_VBA_PROJECT", WIDE("_VBA_PROJECT"), WIDE("Macros")])) state.macros ??= path;
	if (kind === "pdf" && holds(bytes, ["/JavaScript", "/JS ", "/JS(", "/Launch"])) state.scripts ??= path;
	if (kind === "page") state.page ??= path;
}

async function walk(bytes, path, depth, state, programs, listed) {
	let kind = sniff(bytes);
	if (listed) {
		state.count += 1;
		if (state.count > LIMITS.entries) throw new Stop("too_many");
	}
	if (kind === "zip") {
		const entries = central(bytes);
		kind = zipKind(entries.map((one) => one.name));
		if (kind === "program") state.program ??= path;
		const own = kind === "zip";
		for (const entry of entries) {
			if (entry.name.endsWith("/")) continue;
			const inner = `${path}/${entry.name}`;
			const named = entry.name.toLowerCase();
			if (named.endsWith("vbaproject.bin") || (kind === "odf" && (named.startsWith("basic/") || named.startsWith("scripts/")))) state.macros ??= path;
			if (depth >= LIMITS.depth) {
				if (own) throw new Stop("too_deep");
				continue;
			}
			const data = await entryOf(bytes, entry, state);
			const found = await walk(data, inner, depth + 1, state, programs, own);
			if (own && state.inside.length < LIMITS.listed) state.inside.push({ path: inner.split("/").slice(1).join("/"), size: data.length, kind: found });
		}
	} else if (kind === "gzip" || kind === "tar") {
		if (depth >= LIMITS.depth) throw new Stop("too_deep");
		const unzipped = () => path.split("/").pop().replace(/\.tgz$/i, ".tar").replace(/\.gz$/i, "");
		const entries = kind === "gzip" ? [{ name: unzipped(), data: await inflated(bytes, "gzip", LIMITS.entry, state) }] : tarEntries(bytes);
		for (const entry of entries) {
			const inner = `${path}/${entry.name}`;
			const found = await walk(entry.data, inner, depth + 1, state, programs, true);
			if (state.inside.length < LIMITS.listed) state.inside.push({ path: inner.split("/").slice(1).join("/"), size: entry.data.length, kind: found });
		}
	} else if (kind === "unopened") {
		throw new Stop("unopened");
	}
	leaf(path, kind, bytes, state, programs);
	return kind;
}

export async function inspect(name, bytes, programs = []) {
	const state = { count: 0, bytes: 0, inside: [], program: null, macros: null, scripts: null, page: null };
	const named = ending(name);
	let kind = sniff(bytes);
	let unchecked = null;
	try {
		kind = await walk(bytes, String(name || "file"), 0, state, new Set(programs.map((one) => String(one).toLowerCase())), false);
	} catch (stopped) {
		if (!(stopped instanceof Stop)) throw stopped;
		unchecked = stopped.why;
	}
	const top = (path) => (path ? path.split("/").slice(1).join("/") || path : null);
	return {
		kind,
		named,
		mismatch: Boolean(EXPECTED[named] && kind !== "unknown" && !EXPECTED[named].includes(kind)),
		program: top(state.program),
		macros: top(state.macros),
		scripts: Boolean(state.scripts),
		page: Boolean(state.page),
		inside: state.inside,
		count: state.count,
		unchecked,
		office: OFFICE.has(kind) && !state.program && !unchecked,
		ending: OFFICE.has(kind) ? (EXPECTED[named]?.includes(kind) ? named : ENDINGS[kind]) : null,
	};
}

export function allowed(url) {
	if (typeof url !== "string" || url.length > 2048) return false;
	try {
		const parsed = new URL(url);
		return (parsed.protocol === "https:" || parsed.protocol === "http:") && !parsed.username && !parsed.password && Boolean(parsed.hostname);
	} catch {
		return false;
	}
}

const pause = (ms) => new Promise((done) => setTimeout(done, ms));

async function asksPassword(page) {
	for (const frame of page.frames()) {
		const found = await frame.$('input[type="password"]').catch(() => null);
		if (found) return true;
	}
	return false;
}

export async function see(open, url, limits = LIMITS) {
	const browser = await open();
	let timer;
	const looked = (async () => {
		const page = await browser.newPage();
		await page.setViewport({ width: 1280, height: 800 });
		let response = null;
		let failed = null;
		try {
			response = await page.goto(url, { waitUntil: "load", timeout: limits.wait });
		} catch (raised) {
			failed = /ERR_ABORTED/.test(String(raised?.message || raised)) ? "download" : /timeout/i.test(String(raised?.message || raised)) ? "slow" : "unreachable";
		}
		if (failed !== "unreachable" && failed !== "download") await pause(limits.settle);
		const redirects = response ? response.request().redirectChain().map((one) => one.url()) : [];
		return {
			url,
			final_url: failed === "unreachable" || failed === "download" ? url : page.url(),
			redirects,
			status: response ? response.status() : null,
			title: failed === "unreachable" ? "" : await page.title().catch(() => ""),
			asks_password: failed === "unreachable" ? false : await asksPassword(page),
			picture: failed === "unreachable" || failed === "download" ? null : await page.screenshot({ type: "jpeg", quality: 60, encoding: "base64" }).catch(() => null),
			failed,
		};
	})();
	const late = new Promise((_, refuse) => (timer = setTimeout(() => refuse(new Stop("slow")), limits.most)));
	try {
		return await Promise.race([looked, late]);
	} catch (raised) {
		if (raised instanceof Stop) return { url, final_url: url, redirects: [], status: null, title: "", asks_password: false, picture: null, failed: "slow" };
		throw raised;
	} finally {
		clearTimeout(timer);
		await browser.close().catch(() => {});
	}
}
