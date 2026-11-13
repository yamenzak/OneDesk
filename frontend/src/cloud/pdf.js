// A PDF read in the page with PDF.js (pdfjs-dist, Apache-2.0), loaded only
// when one is opened. Its bytes come from OneCloud's own address
// (one_cloud/api.py content), since the store's may not be read by a page.
import { contentUrl } from "./cloud";

let library = null;

async function load() {
	if (library) return library;
	const [lib, worker] = await Promise.all([import("pdfjs-dist"), import("pdfjs-dist/build/pdf.worker.min.mjs?url")]);
	lib.GlobalWorkerOptions.workerSrc = worker.default;
	library = lib;
	return lib;
}

export async function openPdf(node, src = null) {
	const lib = await load();
	const answer = await fetch(src || contentUrl(node), { credentials: "same-origin" });
	if (!answer.ok) throw new Error(await refusal(answer));
	return lib.getDocument({ data: new Uint8Array(await answer.arrayBuffer()) }).promise;
}

// What the server said when it refused, from frappe's error answer.
async function refusal(answer) {
	try {
		const said = await answer.json();
		const first = JSON.parse(said._server_messages || "[]")[0];
		return (first && JSON.parse(first).message) || said.exception || `${answer.status}`;
	} catch {
		return `${answer.status}`;
	}
}

// One page drawn on a canvas at a width, sharp on a dense screen.
export async function drawPage(pdf, number, canvas, width) {
	const page = await pdf.getPage(number);
	const plain = page.getViewport({ scale: 1 });
	const scale = width / plain.width;
	const dense = Math.min(2, globalThis.devicePixelRatio || 1);
	const viewport = page.getViewport({ scale: scale * dense });
	canvas.width = viewport.width;
	canvas.height = viewport.height;
	canvas.style.width = `${Math.round(viewport.width / dense)}px`;
	canvas.style.height = `${Math.round(viewport.height / dense)}px`;
	await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
}
