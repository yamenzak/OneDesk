<!-- Insert a Field: one of the fields of the record the document is on, as a block that prints the record's value (shim/field.js, one_doc/paper.py). -->
<template>
	<Dialog v-model:open="open" :title="__('Insert a Field')" size="lg">
		<template #default>
			<div class="flex flex-col gap-3">
				<p class="text-sm text-ink-gray-5">{{ __("A field prints what {0} says when the document is printed.", [record?.name || ""]) }}</p>
				<FormControl v-model="search" type="text" :placeholder="__('Search fields')" autofocus />
				<div class="flex max-h-96 flex-col overflow-y-auto">
					<button
						v-for="one in shown"
						:key="one.field"
						class="flex items-baseline gap-3 rounded-2 px-2 py-1.5 text-left hover:bg-surface-gray-2"
						@click="insert(one)"
					>
						<span class="shrink-0 text-base text-ink-gray-8">{{ one.label }}</span>
						<span class="truncate text-sm text-ink-gray-5">{{ one.value }}</span>
					</button>
					<p v-if="!shown.length" class="px-2 py-1.5 text-sm text-ink-gray-5">{{ loading ? __("Loading…") : __("No field matches.") }}</p>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, FormControl } from "frappe-ui";
import { computed, ref, watch } from "vue";

import { __, call } from "../../kit/desk";

const props = defineProps({
	modelValue: Boolean,
	document: { type: String, default: "" },
	record: { type: Object, default: null },
	editor: { type: Object, default: null },
});
const emit = defineEmits(["update:modelValue"]);
const open = computed({ get: () => props.modelValue, set: (said) => emit("update:modelValue", said) });
const fields = ref([]);
const search = ref("");
const loading = ref(false);

const shown = computed(() => {
	const wanted = search.value.trim().toLowerCase();
	return wanted ? fields.value.filter((one) => one.label.toLowerCase().includes(wanted) || one.field.includes(wanted)) : fields.value;
});

watch(open, async (now) => {
	if (!now) return;
	search.value = "";
	loading.value = true;
	try {
		fields.value = (await call("onedesk.one_doc.paper.fields_of", { name: props.document })) || [];
	} finally {
		loading.value = false;
	}
});

function insert(one) {
	props.editor?.chain().focus().insertRecordField(one.field, one.label).run();
	open.value = false;
}
</script>
