// The portal, a Frappe UI app (onedesk/one/portal.py, docs in
// onedesk/one/README.md under The Portal), built the way frappe-ui builds
// one: its page to onedesk/www/portal.html, its files beside the islands'.
import path from "node:path";
import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [
		frappeui({
			frontendRoute: "/portal",
			// The page sets frappe.boot itself (index.html).
			jinjaBootData: false,
			buildConfig: {
				outDir: path.resolve(import.meta.dirname, "../../onedesk/public/dist/portal"),
				baseUrl: "/assets/onedesk/dist/portal/",
				indexHtmlPath: path.resolve(import.meta.dirname, "../../onedesk/www/portal.html"),
			},
		}),
		vue(),
	],
	resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
});
