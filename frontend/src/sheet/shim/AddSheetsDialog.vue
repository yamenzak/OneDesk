<!-- Add a template's sheets to the workbook that is open (one_sheet/templates.py, sheets_of): those made for this workbook's table first, then every other, a table's own sheet left out. -->
<template>
	<Dialog v-model:open="open" :title="__('Add Sheets From a Template')" size="md">
		<template #default>
			<div class="flex flex-col gap-2">
				<p v-if="loading" class="text-sm text-ink-gray-5">{{ __("Loading…") }}</p>
				<p v-else-if="!offered.length" class="text-sm text-ink-gray-5">{{ __("There are no templates yet. Save one from File › Save as Template.") }}</p>
				<Button v-for="one in offered" :key="one.name" class="w-full justify-start" :loading="busy === one.name" @click="pick(one.name)">
					{{ one.title }}
				</Button>
				<p v-if="error" class="text-sm text-ink-red-4">{{ error }}</p>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { __ } from "../../kit/desk";
import { call } from "../utils/api.js";

const props = defineProps({ modelValue: Boolean, bound: { type: Object, default: null } });
const emit = defineEmits(["update:modelValue", "add"]);
const open = computed({ get: () => props.modelValue, set: (said) => emit("update:modelValue", said) });
const offered = ref([]);
const loading = ref(false);
const busy = ref("");
const error = ref("");

watch(open, async (now) => {
	if (!now) return;
	error.value = "";
	loading.value = true;
	try {
		const every = await call("onedesk.one_sheet.templates.listed", { every: 1 });
		const mine = props.bound ? await call("onedesk.one_sheet.templates.listed", { doctype: props.bound.doctype, field: props.bound.field }) : [];
		const first = new Set((mine || []).map((one) => one.name));
		offered.value = [...(mine || []), ...(every || []).filter((one) => !first.has(one.name))];
	} catch (failed) {
		error.value = failed?.message || __("The templates couldn’t be loaded.");
	} finally {
		loading.value = false;
	}
});

async function pick(name) {
	busy.value = name;
	error.value = "";
	try {
		emit("add", await call("onedesk.one_sheet.templates.sheets_of", { template: name }));
		open.value = false;
	} catch (failed) {
		error.value = failed?.message || __("The sheets weren’t added.");
	} finally {
		busy.value = "";
	}
}
</script>
