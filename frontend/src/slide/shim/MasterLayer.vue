<!-- What the presentation's master draws under the slide in the editor
     (shim/master.js): there to see, never chosen or moved from here. -->
<template>
	<div v-if="drawn.length" class="pointer-events-none absolute inset-0 isolate">
		<SlideElement v-for="element in drawn" :key="element.id" mode="thumbnail" :element="element" />
	</div>
</template>

<script setup>
import { computed } from "vue";
import SlideElement from "../components/SlideElement.vue";
import { underneath } from "./master.js";

const props = defineProps({
	slide: { type: Object, default: null },
	index: { type: Number, default: -1 },
});

const drawn = computed(() => underneath(props.slide, props.index));
</script>
