<!-- Save this workbook as a template (one_sheet/templates.py): a name, and who will see it. -->
<template>
	<Dialog v-model:open="open" :title="__('Save as Template')" size="md">
		<template #default>
			<div class="flex flex-col gap-3">
				<FormControl v-model="title" type="text" :label="__('Name')" :placeholder="__('e.g. Costing')" />
				<p class="text-sm text-ink-gray-5">
					{{ bound ? __("It keeps every sheet and the formulas in the table, but not the table's rows.") : __("It keeps every sheet as it is now.") }}
					<Branded :text="__('It goes in OneCloud › Workbook Templates, where everyone in the company can start from it.')" />
				</p>
				<p v-if="error" class="text-sm text-ink-red-4">{{ error }}</p>
			</div>
		</template>
		<template #actions>
			<Button variant="solid" class="w-full" :loading="busy" :disabled="!title.trim()" @click="save">{{ __("Save as Template") }}</Button>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog, FormControl } from "frappe-ui";
import { computed, ref, watch } from "vue";
import Branded from "../../kit/Branded.vue";
import { __ } from "../../kit/desk";
import { call } from "../utils/api.js";

const props = defineProps({ modelValue: Boolean, workbook: { type: String, default: "" }, name: { type: String, default: "" }, bound: { type: Object, default: null } });
const emit = defineEmits(["update:modelValue", "saved"]);
const open = computed({ get: () => props.modelValue, set: (said) => emit("update:modelValue", said) });
const title = ref("");
const busy = ref(false);
const error = ref("");

watch(open, (now) => {
	if (now) {
		title.value = props.name;
		error.value = "";
	}
});

async function save() {
	busy.value = true;
	error.value = "";
	try {
		const made = await call("onedesk.one_sheet.templates.save_as", { name: props.workbook, title: title.value.trim() });
		emit("saved", made);
		open.value = false;
	} catch (failed) {
		error.value = failed?.message || __("The template wasn’t saved.");
	} finally {
		busy.value = false;
	}
}
</script>
