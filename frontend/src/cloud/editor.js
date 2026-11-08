// Derived from frappe/ui src/components/FileUpload/ImageCropper.vue
// Copyright (c) 2016-2021 Frappe Technologies Pvt. Ltd., MIT.

export const EDITS = ["png", "jpg", "jpeg", "webp"];

const TYPES = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp" };

export const filterOf = ({ brightness = 0, contrast = 0, saturation = 0 } = {}) =>
	`brightness(${100 + brightness}%) contrast(${100 + contrast}%) saturate(${100 + saturation}%)`;

export async function startEditor(picture) {
	const { default: Cropper } = await import("cropperjs");
	const cropper = new Cropper(picture);
	const stage = cropper.getCropperCanvas();
	stage.style.width = "100%";
	stage.style.height = "100%";
	const image = cropper.getCropperImage();
	const selection = cropper.getCropperSelection();
	await image.$ready();
	const editor = { cropper, stage, image, selection, ratio: NaN, angle: 0 };
	await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
	settle(editor);
	selection.addEventListener("change", (event) => {
		if (!inside(editor, event.detail)) event.preventDefault();
	});
	return editor;
}

function bounds({ stage, image }) {
	const outer = stage.getBoundingClientRect();
	const shown = image.getBoundingClientRect();
	return { x: shown.left - outer.left, y: shown.top - outer.top, width: shown.width, height: shown.height };
}

function inside(editor, box) {
	const room = bounds(editor);
	const near = 0.5;
	return box.x >= room.x - near && box.y >= room.y - near && box.x + box.width <= room.x + room.width + near && box.y + box.height <= room.y + room.height + near;
}

export function fit(editor, ratio = editor.ratio) {
	editor.ratio = ratio;
	const room = bounds(editor);
	let { width, height } = room;
	if (ratio > 0) {
		if (width / height > ratio) width = height * ratio;
		else height = width / ratio;
	}
	editor.selection.aspectRatio = NaN;
	editor.selection.$change(room.x + (room.width - width) / 2, room.y + (room.height - height) / 2, width, height);
	editor.selection.aspectRatio = ratio > 0 ? ratio : NaN;
}

function settle(editor) {
	editor.image.$center("contain");
	fit(editor);
}

export function turn(editor, degrees) {
	editor.image.$rotate(`${degrees}deg`);
	settle(editor);
}

export function straighten(editor, angle) {
	editor.image.$rotate(`${angle - editor.angle}deg`);
	editor.angle = angle;
	settle(editor);
}

export function flip(editor, across) {
	editor.image.$scale(across ? -1 : 1, across ? 1 : -1);
	settle(editor);
}

export function reset(editor) {
	editor.image.$resetTransform();
	editor.angle = 0;
	settle(editor);
}

export function look(editor, adjust) {
	editor.image.style.filter = filterOf(adjust);
}

export function fullWidth({ image, selection }) {
	const [a, b] = image.$getTransform();
	return Math.round(selection.width / Math.hypot(a, b));
}

export async function finished(editor, { extension, width, adjust }) {
	const type = TYPES[extension] || "image/png";
	const canvas = await editor.selection.$toCanvas({
		width: width || fullWidth(editor),
		beforeDraw(context, drawn) {
			if (type === "image/jpeg") {
				context.fillStyle = "white";
				context.fillRect(0, 0, drawn.width, drawn.height);
			}
			context.filter = filterOf(adjust);
			context.imageSmoothingQuality = "high";
		},
	});
	return new Promise((done) => canvas.toBlob(done, type, 0.92));
}

export const stopEditor = (editor) => editor?.cropper?.destroy?.();
