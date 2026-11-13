import { existsSync, readdirSync, readFileSync } from "node:fs";

import preset, { content } from "frappe-ui/tailwind";

// The icons the app draws by name, so tailwind keeps their classes: each tab's,
// declared by a module's portal.py (the one_portal hook, which the registry
// builds from those files, onedesk/one/registry/hooks.py), and the account's.
const app = new URL("../../onedesk/", import.meta.url);
const read = (path) => readFileSync(new URL(path, app), "utf8");
const declared = readdirSync(app)
	.filter((folder) => folder !== "one_portal" && existsSync(new URL(`${folder}/portal.py`, app)))
	.map((folder) => read(`${folder}/portal.py`));
const engine = read("one_portal/portal.py");
const icons = [
	...declared.flatMap((source) => [...source.matchAll(/"icon":\s*"([\w-]+)"/g)]),
	...engine.split("ACCOUNT = ")[1].split("\n)")[0].matchAll(/,\s*"([\w-]+)"\)/g),
].map((found) => `lucide-${found[1]}`);

export default {
	presets: [preset],
	content: [...content, "./index.html", "./src/**/*.{vue,js}"],
	safelist: [...new Set([...icons, "lucide-file-text"])],
};
