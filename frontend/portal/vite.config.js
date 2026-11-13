import path from "node:path";
import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [
		frappeui({
			frontendRoute: "/portal",
			jinjaBootData: false,
			buildConfig: {
				outDir: path.resolve(import.meta.dirname, "../../onedesk/public/dist/portal"),
				baseUrl: "/assets/onedesk/dist/portal/",
				indexHtmlPath: path.resolve(import.meta.dirname, "../../onedesk/www/portal.html"),
			},
		}),
		vue(),
	],
	resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") }, dedupe: ["reka-ui"] },
});
