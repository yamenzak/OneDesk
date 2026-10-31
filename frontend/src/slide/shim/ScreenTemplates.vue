<!-- Templates on a screen: premade screens to start from, the ones for this
     screen's shape first (one_display/starters.py). Choosing one puts it on
     the canvas in place of what is there, as one step that undoes. One's
     own; VENDORED.md. -->
<template>
	<Dialog v-model:open="open" :title="__('Templates')" size="5xl">
		<div class="flex flex-col gap-4">
			<div class="flex flex-wrap gap-1.5">
				<Button v-for="one in groupOptions" :key="one.value" size="sm" :variant="group === one.value ? 'solid' : 'subtle'" :label="one.label" @click="group = one.value" />
			</div>
			<div class="no-scrollbar flex max-h-[32rem] flex-col gap-5 overflow-y-auto">
				<section v-for="shelf in shelves" :key="shelf.key" class="flex flex-col gap-2">
					<span class="text-sm text-ink-gray-5">{{ shelf.label }}</span>
					<div class="grid grid-cols-3 gap-5">
						<button v-for="one in shelf.items" :key="one.key" class="group flex flex-col gap-1.5 text-start disabled:opacity-60" :disabled="!!busy" @click="choose(one)">
							<div class="flex aspect-video w-full items-center justify-center overflow-hidden rounded-6 border border-outline-gray-1 bg-surface-gray-2 group-hover:border-outline-gray-4">
								<img :src="one.picture" :alt="one.label" class="max-h-full max-w-full object-contain" loading="lazy" />
							</div>
							<span class="truncate text-base font-medium text-ink-gray-8">{{ one.label }}</span>
							<span class="line-clamp-2 text-sm text-ink-gray-5">{{ one.about }}</span>
						</button>
					</div>
				</section>
			</div>
		</div>
	</Dialog>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Button, Dialog } from "frappe-ui";
import { commandHistory } from "../stores/historyMeta";
import { batchCommand, editSlideCommand } from "../stores/commands";
import { currentSlide } from "../stores/slide";
import { screen } from "../stores/presentation";
import { call, confirm } from "../../kit/desk";
import { __ } from "./words.js";

const open = defineModel("open", { type: Boolean, default: false });
const said = ref({ shape: "wide", groups: [], starters: [] });
const group = ref("");
const busy = ref("");

const groupOptions = computed(() => [{ value: "", label: __("All") }, ...said.value.groups.map((one) => ({ value: one.key, label: one.label }))]);
const shelves = computed(() => {
	const chosen = said.value.starters.filter((one) => !group.value || one.group === group.value);
	const fits = chosen.filter((one) => one.shape === said.value.shape);
	const rest = chosen.filter((one) => one.shape !== said.value.shape);
	return [
		{ key: "fits", label: __("For This Screen"), items: fits },
		{ key: "rest", label: __("Other Shapes"), items: rest },
	].filter((shelf) => shelf.items.length);
});

watch(
	open,
	(now) => {
		if (now && screen.value && !said.value.starters.length) call("onedesk.one_display.starters.offered", { collection: screen.value.name }).then((answer) => (said.value = answer));
	},
	{ immediate: true }
);

// what the template lays out takes the place of everything on the canvas
function choose(one) {
	const slide = currentSlide.value;
	if (!slide) return;
	if (!slide.elements.length) return put(one, slide);
	confirm(__("Replace what is on this screen with {0}? Undo brings it back.", [one.label]), () => put(one, slide));
}

async function put(one, slide) {
	busy.value = one.key;
	try {
		const made = await call("onedesk.one_display.starters.made", { collection: screen.value.name, starter: one.key });
		commandHistory.execute(
			batchCommand({
				slideId: slide.clientId,
				commands: [
					editSlideCommand({ slideId: slide.clientId, property: "elements", oldValue: slide.elements, newValue: made.elements }),
					editSlideCommand({ slideId: slide.clientId, property: "background", oldValue: slide.background, newValue: made.background }),
				],
			})
		);
		open.value = false;
	} finally {
		busy.value = "";
	}
}
</script>
