<!-- The slide library inside Add Slide (one_slide/library.py): a slide of
     every kind from the decks One ships, and the company's own, by kind.
     Choosing one inserts it like a layout. One's own; VENDORED.md. -->
<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap gap-1.5">
			<Button v-for="one in kindOptions" :key="one.value" size="sm" :variant="kind === one.value ? 'solid' : 'subtle'" :label="one.label" @click="kind = one.value" />
		</div>
		<div class="no-scrollbar flex max-h-[28rem] flex-col gap-5 overflow-y-auto">
			<section v-for="shelf in shown" :key="shelf.key" class="flex flex-col gap-2">
				<span class="text-sm text-ink-gray-5">{{ shelf.label }}</span>
				<div class="grid grid-cols-3 gap-6">
					<div v-for="item in shelf.items" :key="item.client_id" class="group relative cursor-pointer overflow-hidden rounded-6 border border-outline-gray-1 hover:border-outline-gray-3" @click="emit('insert', item)">
						<SlidePreview :slide="item" :scale="PREVIEW_SCALE * (960 / (item.width || 960))" />
						<span class="absolute bottom-1 start-1 rounded-4 bg-surface-base px-1.5 text-xs text-ink-gray-6">{{ said.kinds[item.kind] || "" }}</span>
						<Button v-if="shelf.key === 'yours' && said.may_keep" class="absolute end-1 top-1 opacity-0 group-hover:opacity-100" size="sm" icon="lucide-x" :title="__('Take off the shelf')" @click.stop="forget(item)" />
					</div>
				</div>
			</section>
			<p v-if="!shown.length" class="text-sm text-ink-gray-5">{{ __("No slides of this kind yet. A manager adds one with Save to Library on a slide's menu.") }}</p>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";
import SlidePreview from "../components/SlidePreview.vue";
import { call } from "../../kit/desk";
import { __ } from "./words.js";

// card width: 4xl dialog (896) - px-6 (48) - two gap-6 (48), divided by 3
const PREVIEW_SCALE = 800 / 3 / 960;

const emit = defineEmits(["insert"]);
const said = ref({ kinds: {}, one: [], yours: [], may_keep: false });
const kind = ref("");

const kindOptions = computed(() => [{ value: "", label: __("All") }, ...Object.entries(said.value.kinds).map(([value, label]) => ({ value, label }))]);
const shown = computed(() =>
	[
		{ key: "yours", label: __("Your company's"), items: said.value.yours },
		{ key: "one", label: __("From One"), items: said.value.one },
	]
		.map((shelf) => ({ ...shelf, items: shelf.items.filter((item) => !kind.value || item.kind === kind.value) }))
		.filter((shelf) => shelf.items.length)
);

async function forget(item) {
	said.value = await call("onedesk.one_slide.library.forget", { client_id: item.client_id });
}

call("onedesk.one_slide.library.shelves").then((answer) => (said.value = answer));
</script>
