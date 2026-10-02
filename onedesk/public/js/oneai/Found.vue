<!-- Several records OneAI read at once, as one list.

     A line each: what the record is called, and the one value that tells it
     apart. Three show; the rest wait behind "Show more", and "Open List" goes
     to the desk list on the same filters, which is where a long list is read.
     One record read on its own is still a card (Record.vue). -->
<template>
	<div class="one-ai-found">
		<div class="one-ai-found__head">
			<Icon name="list" size="sm" />
			<span class="one-ai-found__type">{{ __(found.doctype) }}</span>
			<span class="one-ai-found__count">{{ found.total }}</span>
			<button class="one-ai-found__open" @click="openList">{{ __("Open List") }}</button>
		</div>
		<button v-for="row in shown" :key="row.name" class="one-ai-found__row" @click="openRecord(row.name)">
			<span class="one-ai-found__title">{{ row.title || row.name }}</span>
			<span v-if="row.meta" class="one-ai-found__meta" :title="row.meta_label">{{ row.meta }}</span>
		</button>
		<button v-if="hidden" class="one-ai-found__more" @click="unfolded = !unfolded">
			{{ unfolded ? __("Show fewer") : __("Show {0} more", [hidden]) }}
		</button>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Icon from "./Icon.vue";

const __ = window.__;

const props = defineProps({ found: { type: Object, required: true } });

//: Lines shown before "Show more".
const FIRST = 3;
const unfolded = ref(false);
const rows = computed(() => props.found.rows || []);
const shown = computed(() => (unfolded.value ? rows.value : rows.value.slice(0, FIRST)));
const hidden = computed(() => Math.max(rows.value.length - FIRST, 0));

function openRecord(name) {
	frappe.set_route("Form", props.found.doctype, name);
}

function openList() {
	frappe.set_route("List", props.found.doctype, props.found.filters || {});
}
</script>
