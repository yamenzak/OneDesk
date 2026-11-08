import { Container, getContainer } from "@cloudflare/containers";

const ALLOWED = ["/forms/libreoffice/convert", "/forms/pdfengines/merge", "/health"];

export class Office extends Container {
	defaultPort = 3000;
	sleepAfter = "5m";
}

export default {
	async fetch(request, env) {
		const { pathname } = new URL(request.url);
		if (!env.ONE_SECRET || request.headers.get("x-one-secret") !== env.ONE_SECRET) return new Response("Forbidden", { status: 403 });
		if (!ALLOWED.includes(pathname)) return new Response("Not Found", { status: 404 });
		return getContainer(env.OFFICE, "office").fetch(request);
	},
};
