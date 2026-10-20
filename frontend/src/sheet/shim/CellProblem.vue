<!-- What is wrong with the selected cell, under it, and the fix when there is one: a record the table names that isn't there yet is made from here (one_sheet/table.py, make_missing). -->
<template>
	<div role="alert" :style="box" @mousedown.stop>
		<p :style="{ margin: 0, fontWeight: 600, color: tone }">{{ problem.code || (problem.level === 'warn' ? __('Check this') : __('Not taken')) }}</p>
		<p :style="{ margin: '4px 0 0' }">{{ problem.message }}</p>
		<div v-if="problem.doctype && problem.value && canFix" :style="{ marginTop: '8px', display: 'flex', gap: '6px' }">
			<Button size="sm" variant="solid" :loading="busy" @click="fix">{{ __("Create {0}", [__(problem.doctype)]) }}</Button>
		</div>
		<p v-if="failed" :style="{ margin: '6px 0 0', color: 'var(--ink-red-4)' }">{{ failed }}</p>
	</div>
</template>

<script setup>
import { Button } from "frappe-ui";
import { computed, ref } from "vue";
import { __ } from "../../kit/desk";
import { call } from "../utils/api.js";

const props = defineProps({
	problem: { type: Object, required: true },
	workbook: { type: String, default: "" },
	canFix: { type: Boolean, default: true },
	x: { type: Number, default: 0 },
	y: { type: Number, default: 0 },
});
const emit = defineEmits(["fixed"]);
const busy = ref(false);
const failed = ref("");

const tone = computed(() => (props.problem.level === "warn" ? "var(--ink-amber-4)" : "var(--ink-red-4)"));
const box = computed(() => ({
	position: "fixed",
	left: props.x + "px",
	top: props.y + "px",
	width: "280px",
	zIndex: 8400,
	padding: "var(--padding-sm, 8px) var(--padding-md, 12px)",
	fontSize: "var(--text-sm, 13px)",
	lineHeight: 1.45,
	color: "var(--text-color, var(--ink-gray-8))",
	backgroundColor: "var(--bg-color, var(--surface-white))",
	border: "1px solid var(--border-color, var(--outline-gray-2))",
	borderTop: `3px solid ${tone.value}`,
	borderRadius: "var(--radius, 8px)",
	boxShadow: "var(--shadow-md)",
}));

async function fix() {
	busy.value = true;
	failed.value = "";
	try {
		const said = await call("onedesk.one_sheet.table.make_missing", {
			name: props.workbook,
			doctype: props.problem.doctype,
			values: JSON.stringify([props.problem.value]),
		});
		const why = (said?.failed || {})[props.problem.value];
		if (why) failed.value = why;
		else emit("fixed", props.problem);
	} catch (error) {
		failed.value = error?.message || __("It couldn’t be made.");
	} finally {
		busy.value = false;
	}
}
</script>
