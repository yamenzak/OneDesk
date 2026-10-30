<!-- The slide's own choice about the presentation's master, in the panel with
     nothing chosen (shim/master.js). One's own; VENDORED.md. -->
<template>
	<Section :label="__('Master')">
		<div class="flex items-center justify-between">
			<span class="text-sm text-ink-gray-7">{{ __("Show the Master") }}</span>
			<Switch :model-value="!currentSlide?.hideMaster" @update:model-value="toggle" />
		</div>
	</Section>
</template>

<script setup>
import { Switch } from "frappe-ui";
import Section from "../components/controls/Section.vue";
import { useSlideProperty } from "../composables/editProperty";
import { currentSlide } from "../stores/slide";
import { __ } from "./words.js";

const hidden = useSlideProperty("hideMaster");

function toggle(shown) {
	hidden.begin();
	hidden.set(shown ? 0 : 1);
	hidden.commit();
}
</script>
