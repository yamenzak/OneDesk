<!-- Who looked at the presentation through its OneCloud links, when and for
     how long, and how long each slide held them (one_deck/shared.py views).
     One's own; VENDORED.md. -->
<template>
	<Dialog v-model:open="open" :title="__('Views')" size="lg">
		<div class="flex flex-col gap-4">
			<p v-if="!said.looks.length" class="text-base text-ink-gray-6">{{ __("Nobody has opened this presentation through a link yet. Share it from {0} with a link, and each look shows here.", [appName("one_cloud")]) }}</p>
			<template v-else>
				<div class="flex flex-col">
					<p class="mb-1 text-sm font-medium text-ink-gray-5">{{ __("Looks") }}</p>
					<div v-for="(one, at) in said.looks" :key="at" class="flex items-center gap-3 border-b border-outline-gray-1 py-2 text-base">
						<span class="min-w-0 flex-1 truncate text-ink-gray-8">{{ one.viewer }}</span>
						<span class="text-ink-gray-5">{{ when(one.opened_on) }}</span>
						<span class="w-20 text-end text-ink-gray-7">{{ length(one.total) }}</span>
					</div>
				</div>
				<div class="flex flex-col">
					<p class="mb-1 text-sm font-medium text-ink-gray-5">{{ __("Time on Each Slide") }}</p>
					<div v-for="one in said.slides" :key="one.number" class="flex items-center gap-3 border-b border-outline-gray-1 py-2 text-base">
						<span class="flex-1 text-ink-gray-8">{{ __("Slide {0}", [one.number]) }}</span>
						<span class="w-20 text-end text-ink-gray-7">{{ length(one.seconds) }}</span>
					</div>
				</div>
			</template>
		</div>
	</Dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { Dialog } from "frappe-ui";
import { ago, call, duration, name as appName } from "../../kit/desk";
import { __ } from "./words.js";

const open = defineModel({ type: Boolean, default: false });
const props = defineProps({ name: { type: String, required: true } });
const said = ref({ looks: [], slides: [] });

watch(open, async (now) => {
	if (now) said.value = await call("onedesk.one_deck.shared.views", { name: props.name });
});

const when = (value) => ago(value);
const length = (seconds) => duration(seconds || 0);
</script>
