import { readFileSync } from "node:fs";

import preset, { content } from "frappe-ui/tailwind";

// The icons the app draws by name, so tailwind keeps their classes: each tab's,
// declared by its module's portal.py (the one_portal hook), and the account's.
const read = (path) => readFileSync(new URL(`../../onedesk/${path}`, import.meta.url), "utf8");
const hook = read("hooks.py").split("one_portal = [")[1].split("]")[0];
const declared = [...hook.matchAll(/"onedesk\.([\w.]+)"/g)].map((found) => read(`${found[1].replace(/\./g, "/")}.py`));
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
