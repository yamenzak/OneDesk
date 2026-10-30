<!-- How the selected element comes in and goes out (shim/motion.js, one_slide/motion.json). One's own; VENDORED.md. -->
<template>
	<Section :label="__('Motion')">
		<PropertyRow :label="__('Comes In')">
			<Select :modelValue="motion.in || ''" variant="ghost" :options="choices('in')" class="-me-1" @update:modelValue="(value) => set({ in: value || null })" />
		</PropertyRow>
		<PropertyRow :label="__('Goes Out')">
			<Select :modelValue="motion.out || ''" variant="ghost" :options="choices('out')" class="-me-1" @update:modelValue="(value) => set({ out: value || null })" />
		</PropertyRow>
		<template v-if="motion.in || motion.out">
			<PropertyRow v-if="flies" :label="__('Direction')">
				<Select :modelValue="motion.from || 'Left'" variant="ghost" :options="sides" class="-me-1" @update:modelValue="(value) => set({ from: value })" />
			</PropertyRow>
			<!-- a screen has nobody to click, so on a screen it comes after the one before it -->
			<PropertyRow v-if="!screen" :label="__('Starts')">
				<Select :modelValue="motion.start || starts[0].value" variant="ghost" :options="starts" class="-me-1" @update:modelValue="(value) => set({ start: value })" />
			</PropertyRow>
			<NumberControl :modelValue="motion.wait || 0" :label="__('Delay')" suffix="s" :min="0" :max="table.longest" :max-digits="3" :step="0.5" @update:modelValue="(value) => set({ wait: Number(value) || 0 })" />
			<NumberControl :modelValue="motion.speed || table.speed" :label="__('Duration')" suffix="s" :min="0.1" :max="10" :max-digits="2" :step="0.1" @update:modelValue="(value) => set({ speed: Number(value) || table.speed })" />
			<template v-if="motion.out">
				<NumberControl :modelValue="motion.stay || 0" :label="__('Shown For')" suffix="s" :min="0" :max="table.longest" :max-digits="3" :step="0.5" @update:modelValue="(value) => set({ stay: Number(value) || 0 })" />
				<PropertyRow :label="__('Repeat')" class="cursor-pointer">
					<Switch :modelValue="Boolean(motion.again)" :disabled="!(motion.stay > 0)" @update:modelValue="(value) => set({ again: value })" />
				</PropertyRow>
			</template>
		</template>
	</Section>
</template>

<script setup>
import { computed } from "vue";
import { Select, Switch } from "frappe-ui";

import NumberControl from "../components/controls/NumberControl.vue";
import PropertyRow from "../components/controls/PropertyRow.vue";
import Section from "../components/controls/Section.vue";
import { setElementProperty } from "../composables/editProperty";
import { firstEditableElement } from "../stores/element";
import { screen } from "../stores/presentation";
import table from "../../../../onedesk/one_slide/motion.json";
import { __ } from "./words.js";

const motion = computed(() => firstEditableElement.value?.motion || {});
const flies = computed(() => motion.value.in === "Fly In" || motion.value.out === "Fly Out");

const choices = (way) => [{ label: __("None"), value: "" }, ...Object.keys(table[way]).map((name) => ({ label: __(name), value: name }))];
const sides = Object.keys(table.from).map((side) => ({ label: __(side), value: side }));
const starts = table.start.map((start) => ({ label: __(start), value: start }));

// a motion with neither way left is no motion at all
function set(change) {
	const next = { ...motion.value, ...change };
	setElementProperty("motion", next.in || next.out ? next : undefined);
}
</script>
