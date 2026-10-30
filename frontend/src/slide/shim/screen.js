// A widget put on a screen's canvas (stage 7 of docs/ONESLIDE.md): centred,
// at its kind's size in percent of the screen, above everything, chosen, and
// one undoable step like any element added from the bar.
import { commandHistory } from "../stores/historyMeta";
import { addElementCommand, batchCommand } from "../stores/commands";
import { setActiveElements } from "../stores/element";
import { currentSlide } from "../stores/slide";
import { generateUniqueId } from "../utils/helpers";
import { frame } from "./frame.js";

export function addWidget(kind) {
	const slide = currentSlide.value;
	if (!slide) return;
	const [w, h] = kind.size || [30, 30];
	const width = (w / 100) * frame.w;
	const height = (h / 100) * frame.h;
	const element = {
		id: generateUniqueId(),
		type: "widget",
		name: "",
		left: (frame.w - width) / 2,
		top: (frame.h - height) / 2,
		width,
		height,
		zIndex: Math.max(0, ...slide.elements.map((one) => one.zIndex || 0)) + 1,
		// the look its kind starts in (one_display/widgets.py FIRST_LOOK)
		...(kind.look || {}),
		widget: { id: null, widget_type: kind.type, label: "", source: "", mapping: {}, settings: {}, shown: "Always" },
	};
	commandHistory.execute(batchCommand({ slideId: slide.clientId, elementIds: [element.id], commands: [addElementCommand({ slideId: slide.clientId, element })] }));
	setActiveElements([element.id]);
}
