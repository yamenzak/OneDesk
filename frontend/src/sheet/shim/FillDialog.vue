<!-- Fill the record's table from another sheet (one_sheet/table.py, set_map): which sheet, from which row, and where each column comes from. -->
<template>
	<Dialog v-model:open="open" :title="__('Fill the Table From a Sheet')" size="xl">
		<template #default>
			<div class="flex flex-col gap-4">
				<p class="text-sm text-ink-gray-5">
					{{ __("Each line of the source sheet becomes a row of the table, from the first row down, until the key column is empty. A column is a letter, such as B, or a formula that reads the source line: {0}.", ['=C{r}*D{r}']) }}
				</p>
				<div class="grid grid-cols-3 gap-3">
					<FormControl v-model="form.sheet" type="select" :label="__('Source Sheet')" :options="sources" />
					<FormControl v-model="form.first" type="number" :label="__('First Row')" />
					<FormControl v-model="form.key" type="text" :label="__('Key Column')" :placeholder="__('e.g. A')" />
				</div>
				<div class="grid grid-cols-2 gap-x-4 gap-y-2">
					<FormControl v-for="col in bound.columns" :key="col.fieldname" v-model="form.columns[col.fieldname]" type="text" :label="col.header" :placeholder="__('Not filled')" />
				</div>
				<p v-if="error" class="text-sm text-ink-red-4">{{ error }}</p>
			</div>
		</template>
		<template #actions>
			<div class="flex gap-2">
				<Button v-if="bound.fill_map" :loading="busy" @click="save(true)">{{ __("Stop Filling") }}</Button>
				<Button variant="solid" class="flex-1" :loading="busy" :disabled="!form.sheet" @click="save(false)">{{ __("Fill the Table") }}</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog, FormControl } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";
import { __ } from "../../kit/desk";
import { call } from "../utils/api.js";

const props = defineProps({ modelValue: Boolean, workbook: { type: String, default: "" }, bound: { type: Object, required: true }, sheets: { type: Array, default: () => [] } });
const emit = defineEmits(["update:modelValue", "filled"]);
const open = computed({ get: () => props.modelValue, set: (said) => emit("update:modelValue", said) });
const sources = computed(() => props.sheets.filter((one) => one !== props.bound.sheet).map((one) => ({ label: one, value: one })));
const form = reactive({ sheet: "", first: 2, key: "", columns: {} });
const busy = ref(false);
const error = ref("");

watch(open, (now) => {
	if (!now) return;
	const held = props.bound.fill_map || {};
	form.sheet = held.sheet || sources.value[0]?.value || "";
	form.first = held.first || 2;
	form.key = held.key || "";
	form.columns = { ...(held.columns || {}) };
	error.value = "";
});

async function save(stop) {
	busy.value = true;
	error.value = "";
	try {
		const fill_map = stop ? null : JSON.stringify({ sheet: form.sheet, first: Number(form.first) || 2, key: form.key, columns: form.columns });
		const said = await call("onedesk.one_sheet.table.set_map", { name: props.workbook, fill_map });
		emit("filled", { cells: said.cells || {}, fill_map: stop ? null : JSON.parse(fill_map) });
		open.value = false;
	} catch (failed) {
		error.value = failed?.message || __("The table wasn’t filled.");
	} finally {
		busy.value = false;
	}
}
</script>
