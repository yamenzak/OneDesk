<!-- What Suite's Drive rename input does for the workbook's title: edit in place, Enter keeps, Escape drops. -->
<template>
	<input
		ref="input"
		v-model="value"
		type="text"
		spellcheck="false"
		class="min-w-[4ch] max-w-full rounded-1 border-0 bg-surface-base px-0.5 py-1 text-lg font-medium text-ink-gray-9 outline-none focus:outline-none focus:ring-0"
		@keydown.stop
		@keydown.enter.prevent="emit('submit', value)"
		@keydown.escape.prevent="emit('cancel')"
		@blur="emit('blur', value)"
	/>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";

const props = defineProps({ modelValue: { type: String, default: "" }, editing: Boolean, appearance: String });
const emit = defineEmits(["update:modelValue", "submit", "cancel", "blur"]);
const input = ref(null);
const value = computed({ get: () => props.modelValue, set: (said) => emit("update:modelValue", said) });

onMounted(() => nextTick(() => input.value?.select()));
</script>
