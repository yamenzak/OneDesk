<!-- Pictures of slides as the editor draws them: each is put on a hidden stage at its own size, in Suite's own preview, and photographed at twice that, so a page of the PDF, or a screen, shows exactly what was made. -->
<template>
	<div class="pointer-events-none fixed left-[-10000px] top-0 overflow-hidden" aria-hidden="true">
		<div ref="stageEl" class="relative h-[540px] w-[960px] overflow-hidden">
			<SlidePreview v-if="slide" :key="slide.clientId || slide.client_id" :slide="slide" :scale="1" />
		</div>
	</div>
</template>

<script setup>
import { nextTick, ref } from "vue";

import SlidePreview from "../components/SlidePreview.vue";
import { captureDOM } from "../utils/domToWebp.js";

const stageEl = ref(null);
const slide = ref(null);

const settled = (node) =>
	Promise.all(
		[...node.querySelectorAll("img")].map((image) =>
			image.complete ? null : new Promise((done) => image.addEventListener("load", done, { once: true }) || image.addEventListener("error", done, { once: true }))
		)
	);

// One picture a slide, in order. Slides are photographed one at a time, so a
// hundred-slide presentation does not draw a hundred stages at once.
async function shoot(slides, onEach = () => {}) {
	const pictures = [];
	for (const [at, one] of slides.entries()) {
		slide.value = one;
		await nextTick();
		await document.fonts?.ready;
		await settled(stageEl.value);
		pictures.push(await captureDOM(stageEl.value, { scale: 2 }));
		onEach(at + 1, slides.length);
	}
	slide.value = null;
	return pictures;
}

defineExpose({ shoot });
</script>
