// Pictures drawn on this server with DiceBear (MIT, shipped in
// frontend/node_modules), for one/avatars.py: nothing is fetched from
// anywhere. Each style's own licence and creator are written into the SVG it
// draws (its <metadata>), which is the credit a CC BY 4.0 style asks for.
//
//   node draw.mjs styles          [{key, title, creator, license}]
//   node draw.mjs draw < asked    asked: [{style, seed}], says [svg]
import { createAvatar } from "@dicebear/core";
import * as collection from "@dicebear/collection";

const kebab = (name) => name.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
const styles = Object.fromEntries(Object.entries(collection).map(([name, style]) => [kebab(name), style]));

const read = async () => {
	let text = "";
	for await (const chunk of process.stdin) text += chunk;
	return JSON.parse(text || "[]");
};

if (process.argv[2] === "styles") {
	const said = Object.entries(styles).map(([key, style]) => ({
		key,
		title: style.meta?.title || key,
		creator: style.meta?.creator || "",
		license: style.meta?.license?.name || "",
	}));
	process.stdout.write(JSON.stringify(said));
} else if (process.argv[2] === "draw") {
	const asked = await read();
	const said = asked.map(({ style, seed }) => (styles[style] ? createAvatar(styles[style], { seed: String(seed) }).toString() : null));
	process.stdout.write(JSON.stringify(said));
} else {
	process.stderr.write("node draw.mjs styles | draw\n");
	process.exit(2);
}
