<!-- Add Widget on a screen: every kind bare and its ready-made widgets, each
     drawn in its look on the screen's colour (one_display/widgets.py
     PRESETS). Choosing one puts it on the screen. One's own; VENDORED.md. -->
<template>
	<Dialog v-model:open="open" :title="__('Add a Widget')" size="4xl">
		<div class="flex flex-col gap-4">
			<div class="flex flex-wrap gap-1.5">
				<Button v-for="one in kinds" :key="one.value" size="sm" :variant="kind === one.value ? 'solid' : 'subtle'" :label="one.label" @click="kind = one.value" />
			</div>
			<div class="no-scrollbar flex max-h-[30rem] flex-col gap-5 overflow-y-auto">
				<section v-for="group in shown" :key="group.type" class="flex flex-col gap-2">
					<span class="text-sm text-ink-gray-5">{{ group.label }}</span>
					<div class="grid grid-cols-3 gap-4">
						<button v-for="one in group.items" :key="one.key" class="group flex flex-col gap-1.5 text-start" @click="choose(one)">
							<div class="relative aspect-video w-full overflow-hidden rounded-6 border border-outline-gray-1 [container-type:size] group-hover:border-outline-gray-4" :style="{ background: ground }">
								<div class="absolute" :style="placed(one)">
									<WidgetMock :type="one.type" :preset="one.key" :settings="one.settings" :look="one.look" :brand="brand" :on-brand="onBrand" :scale="SCALE" />
								</div>
							</div>
							<span class="truncate text-sm text-ink-gray-7">{{ one.label }}</span>
						</button>
					</div>
				</section>
			</div>
		</div>
	</Dialog>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button, Dialog } from "frappe-ui";
import { screen } from "../stores/presentation";
import WidgetMock from "./WidgetMock.vue";
import { __ } from "./words.js";

// a card is about a third of the 4xl dialog; the editor's frame is 960 wide
const SCALE = 260 / 960;

const open = defineModel("open", { type: Boolean, default: false });
const emit = defineEmits(["add"]);
const kind = ref("");

const brand = computed(() => screen.value?.brand || "");
// the words on the business's colour, as its Accent look has them
const onBrand = computed(() => (screen.value?.looks || []).find((one) => one.name === "Accent")?.look.color || "");
const ground = computed(() => `linear-gradient(135deg, ${brand.value}, color-mix(in srgb, ${brand.value} 45%, black))`);
const types = computed(() => screen.value?.types || []);
const kinds = computed(() => [{ value: "", label: __("All") }, ...types.value.map((one) => ({ value: one.type, label: one.label }))]);
const shown = computed(() =>
	types.value
		.filter((one) => !kind.value || one.type === kind.value)
		.map((one) => ({ type: one.type, label: one.label, items: (screen.value?.presets || []).filter((preset) => preset.type === one.type) }))
		.filter((group) => group.items.length)
);

// how large a kind's words are for its box: the ones with many lines smaller
const DENSE = { "Queue Board": 0.075, Kiosk: 0.09, Board: 0.11, Weather: 0.13 };
// except a layout that shows one thing large
const LARGE = ["latest", "counter", "big", "minimal", "analog", "date"];

// where a widget sits on its card: centred, large enough to read, a whole
// screen's widget filling it
function placed(one) {
	const [w, h] = one.size || [30, 30];
	const wide = w >= 100 ? 100 : Math.min(Math.max(w, 40), 86);
	const high = h >= 100 ? 100 : Math.min(Math.max(h, 26), 80);
	return { left: `${(100 - wide) / 2}%`, top: `${(100 - high) / 2}%`, width: `${wide}%`, height: `${high}%`, fontSize: `${high * (LARGE.includes(one.settings?.layout) ? 0.16 : DENSE[one.type] || 0.16)}cqh` };
}

function choose(one) {
	emit("add", one);
	open.value = false;
}
</script>
