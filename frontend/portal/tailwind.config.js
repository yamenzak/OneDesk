import { readFileSync } from "node:fs";

import preset, { content } from "frappe-ui/tailwind";

const source = readFileSync(new URL("../../onedesk/one/portal.py", import.meta.url), "utf8");
const block = (name, close) => source.split(`${name} = `)[1].split(close)[0];
const icons = [
	...block("ICONS", "\n}").matchAll(/:\s*"([\w-]+)"/g),
	...block("ACCOUNT", "\n)").matchAll(/,\s*"([\w-]+)"\)/g),
].map((found) => `lucide-${found[1]}`);

export default {
	presets: [preset],
	content: [...content, "./index.html", "./src/**/*.{vue,js}"],
	safelist: [...new Set([...icons, "lucide-file-text"])],
};
