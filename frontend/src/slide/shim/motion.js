// How an element comes and goes in the slideshow: the same track the
// player draws on a screen and a shared link (public/js/one_slide/play.js,
// motion), read from the one table both use (one_slide/motion.json). One's
// own; VENDORED.md.
import { ref, watch } from "vue";

import table from "../../../../onedesk/one_slide/motion.json";
import { slideIndex } from "../stores/slide";

// how many of this slide's click entrances have been clicked in
export const clicked = ref(0);
watch(slideIndex, () => (clicked.value = 0));

const num = (value, otherwise = 0) => (Number.isFinite(Number(value)) ? Math.round(Number(value) * 100) / 100 : otherwise);

function state(effect, from) {
	if (!effect) return { o: 1, t: "none" };
	const [x, y] = effect.fly ? table.from[from] || table.from.Left : [0, effect.y || 0];
	return { o: effect.opacity ?? 1, t: `translate(${x}%,${y}%)${effect.scale ? ` scale(${effect.scale})` : ""}` };
}

const frame = (at, look, ease) =>
	`${num(at)}%{opacity:${look.o};transform:${look.t}${ease ? `;animation-timing-function:${ease}` : ""}}`;

// the element's track, or null when it neither comes nor goes
export function motionOf(element, waiting) {
	const m = element.motion || {};
	const enter = table.in[m.in];
	const leave = num(m.stay) > 0 ? table.out[m.out] : null;
	if (!enter && !leave) return null;
	const speed = num(m.speed, table.speed) || table.speed;
	const wait = num(m.wait);
	const inEnds = wait + (enter ? speed : 0);
	const outStarts = inEnds + num(m.stay);
	const total = Math.max(leave ? outStarts + speed : inEnds, 0.01);
	const pct = (t) => (t / total) * 100;
	const first = state(enter, m.from);
	const shown = state(null);
	// named by the element, so a click that only unpauses it does not start it over
	const name = `one-motion-${String(element.id).replace(/[^\w-]/g, "")}`;
	const frames = [frame(0, first), frame(pct(wait), first, "ease-out"), frame(pct(inEnds), shown)];
	frames.push(...(leave ? [frame(pct(outStarts), shown, "ease-in"), frame(100, state(leave, m.from))] : [frame(100, shown)]));
	const middle = `${num(num(element.left) + num(element.width) / 2)}px ${num(num(element.top) + num(element.height) / 2)}px`;
	return {
		keys: `@keyframes ${name}{${frames.join("")}}`,
		look: [
			"position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none",
			`z-index:${Math.max(1, Math.round(num(element.zIndex, 1)))}`,
			`transform-origin:${middle}`,
			`animation:${name} ${num(total)}s linear 0s ${m.again && leave ? "infinite" : 1} both`,
			waiting ? "animation-play-state:paused" : "",
		]
			.filter(Boolean)
			.join(";"),
	};
}

const onClick = (element) => element.motion?.start === "On Click" && motionOf(element);

// the slide's elements, each with its track, a click entrance paused until its turn
export function tracks(elements) {
	let clicks = 0;
	return (elements || []).map((element) => {
		const waiting = element.motion?.start === "On Click" ? clicks++ >= clicked.value : false;
		return { element, moves: motionOf(element, waiting) };
	});
}

// whether a click still has something to bring in on this slide
export const clickWaiting = (elements) => (elements || []).filter(onClick).length > clicked.value;
