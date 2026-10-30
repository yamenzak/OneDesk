<!-- A fill that fades into a second colour: a switch, the colour it fades to and the angle. One's own; VENDORED.md. -->
<template>
	<PropertyRow :label="__('Fade')">
		<Switch :modelValue="!!fade" @update:modelValue="toggle" />
	</PropertyRow>
	<template v-if="fade">
		<PropertyRow :label="__('Fade To')">
			<ColorPicker
				:modelValue="fade.to"
				@update:modelValue="(to) => emit('set', { ...fade, to })"
				@colordown="emit('begin')"
				@colorup="emit('commit')"
			/>
		</PropertyRow>
		<NumberControl
			:modelValue="fade.angle ?? 180"
			:label="__('Fade Angle')"
			suffix="°"
			:min="0"
			:max="360"
			:max-digits="3"
			@update:modelValue="(angle) => emit('set', { ...fade, angle: Number(angle) || 0 })"
			@change-start="emit('begin')"
			@change-end="emit('commit')"
		/>
	</template>
</template>

<script setup>
import { Switch } from 'frappe-ui'

import ColorPicker from '../components/controls/ColorPicker.vue'
import NumberControl from '../components/controls/NumberControl.vue'
import PropertyRow from '../components/controls/PropertyRow.vue'
import { fadePartner } from './looks.js'
import { __ } from './words.js'

const props = defineProps({ fade: Object, from: String })
const emit = defineEmits(['begin', 'set', 'commit', 'toggle'])

const toggle = (on) => emit('toggle', on ? { to: fadePartner(props.from), angle: 180 } : null)
</script>
