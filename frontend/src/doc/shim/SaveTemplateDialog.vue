<!-- Save this document as a template (one_doc/templates.py): a name, and who will see it. -->
<template>
	<Dialog v-model:open="open" :title="__('Save as Template')" size="md">
		<template #default>
			<div class="flex flex-col gap-3">
				<FormControl v-model="title" type="text" :label="__('Name')" :placeholder="__('e.g. Cover letter')" />
				<p class="text-sm text-ink-gray-5">
					{{ __("The template includes the whole document as it is now.") }}
					<Branded :text="__('It is saved to OneCloud › Document Templates and is available to everyone in the company.')" />
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
import { __, alert, call } from "../../kit/desk";

const props = defineProps({ modelValue: Boolean, document: { type: String, default: "" }, name: { type: String, default: "" } });
const emit = defineEmits(["update:modelValue"]);
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
		const made = await call("onedesk.one_doc.templates.save_as", { name: props.document, title: title.value.trim() });
		alert(__("Template {0} saved.", [made.title]));
		open.value = false;
	} catch (failed) {
		error.value = failed?.message || __("Could not save the template.");
	} finally {
		busy.value = false;
	}
}
</script>
