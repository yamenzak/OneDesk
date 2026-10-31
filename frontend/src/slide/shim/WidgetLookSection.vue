<!-- A widget's look (one_display/widgets.py LOOK): a widget draws only its content, and its fill, text colour, highlight, font and padding are its element's, set here; its border and shadow are set in Border and Shadow as any object's. A look is a named set of them. One's own; VENDORED.md. -->
<template>
	<Section :label="__('Look')">
		<PropertyRow :label="__('Look')">
			<Combobox trigger="button" variant="ghost" size="sm" align="end" class="-me-1" :options="lookOptions" :model-value="current" @update:model-value="wear" />
		</PropertyRow>
		<PropertyRow :label="__('Fill')">
			<ColorPicker :modelValue="element.fillColor || ''" @update:modelValue="fill.set" @colordown="fill.begin" @colorup="fill.commit" />
		</PropertyRow>
		<PropertyRow :label="__('Words')">
			<ColorPicker :modelValue="element.color || ''" @update:modelValue="ink.set" @colordown="ink.begin" @colorup="ink.commit" />
		</PropertyRow>
		<PropertyRow :label="__('Highlight')">
			<ColorPicker :modelValue="element.accentColor || ''" @update:modelValue="hi.set" @colordown="hi.begin" @colorup="hi.commit" />
		</PropertyRow>
		<PropertyRow :label="__('Font')">
			<Combobox trigger="button" variant="ghost" size="sm" align="end" class="-me-1" :options="fonts" :model-value="element.fontFamily || ''" @update:model-value="(value) => setElementProperty('fontFamily', value || null)" />
		</PropertyRow>
		<NumberControl :modelValue="element.padding ?? 0" :label="__('Padding')" suffix="px" :min="0" :max="200" :max-digits="3" @update:modelValue="padding.set" @change-start="padding.begin" @change-end="padding.commit" />
	</Section>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { Combobox } from "frappe-ui";
import ColorPicker from "../components/controls/ColorPicker.vue";
import NumberControl from "../components/controls/NumberControl.vue";
import PropertyRow from "../components/controls/PropertyRow.vue";
import Section from "../components/controls/Section.vue";
import { setElementProperties, setElementProperty, useElementProperty } from "../composables/editProperty";
import { firstEditableElement } from "../stores/element";
import { screen } from "../stores/presentation";
import { fontOptions, loadFonts } from "./fonts.js";
import { __ } from "./words.js";

// what a look may set: widgets.LOOK, the same names Border and Shadow write
const KEYS = ["fillColor", "color", "accentColor", "fontFamily", "padding", "borderStyle", "borderColor", "borderWidth", "borderRadius", "shadowColor", "shadowBlur", "shadowOpacity", "shadowOffset", "shadowAngle"];

const element = computed(() => firstEditableElement.value || {});
const fill = useElementProperty("fillColor");
const ink = useElementProperty("color");
const hi = useElementProperty("accentColor");
const padding = useElementProperty("padding");
const fonts = computed(() => [{ group: "", options: [{ label: __("The Screen's"), value: "" }] }, ...fontOptions.value]);
const lookOptions = computed(() => (screen.value?.looks || []).map((one) => ({ label: one.label, value: one.name })));

// the look this element wears now, when it wears one exactly
const current = computed(() => {
	const worn = (screen.value?.looks || []).find((one) => KEYS.every((key) => (one.look[key] ?? null) === (element.value[key] ?? null)));
	return worn?.name || "";
});

// a look replaces every part of the last one, in one step that undoes as one
function wear(name) {
	const look = (screen.value?.looks || []).find((one) => one.name === name)?.look;
	if (!look) return;
	setElementProperties(KEYS.map((property) => ({ property, oldValue: element.value[property] ?? null, newValue: look[property] ?? null })));
}

onMounted(loadFonts);
</script>
