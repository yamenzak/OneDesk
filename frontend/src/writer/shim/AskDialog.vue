<!-- Ask OneAI in a document (one_doc/assist.py): about the selection, or the whole document; words come back to put in, or an answer. -->
<template>
	<Dialog v-model:open="open" :title="__('Ask OneAI')" size="lg">
		<template #default>
			<div class="flex flex-col gap-3">
				<p class="text-sm text-ink-gray-5">{{ selected ? __("About the selected text.") : __("About the whole document. What comes back goes in at the cursor.") }}</p>
				<FormControl v-model="prompt" type="textarea" :rows="3" :placeholder="selected ? __('e.g. Make this shorter and more formal') : __('e.g. Write a paragraph on the payment terms')" />
				<p v-if="answer" class="whitespace-pre-line rounded-2 bg-surface-gray-2 p-3 text-base text-ink-gray-8">{{ answer }}</p>
				<p v-if="error" class="text-sm text-ink-red-4">{{ error }}</p>
			</div>
		</template>
		<template #actions>
			<Button variant="solid" class="w-full" :loading="busy" :disabled="!prompt.trim()" @click="ask">{{ __("Ask") }}</Button>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog, FormControl } from "frappe-ui";
import { computed, ref, watch } from "vue";

import { __, call } from "../../kit/desk";

const props = defineProps({ modelValue: Boolean, document: { type: String, default: "" }, editor: { type: Object, default: null } });
const emit = defineEmits(["update:modelValue"]);
const open = computed({ get: () => props.modelValue, set: (said) => emit("update:modelValue", said) });
const prompt = ref("");
const busy = ref(false);
const error = ref("");
const answer = ref("");
const range = ref(null);

const selected = computed(() => Boolean(range.value && range.value.from !== range.value.to));

watch(open, (now) => {
	if (!now) return;
	error.value = answer.value = "";
	const { from, to } = props.editor?.state.selection || {};
	range.value = props.editor ? { from, to } : null;
});

async function ask() {
	busy.value = true;
	error.value = answer.value = "";
	try {
		const { from, to } = range.value || {};
		const said = await call("onedesk.one_doc.assist.ai_assist", {
			name: props.document,
			prompt: prompt.value.trim(),
			selection: selected.value ? props.editor.state.doc.textBetween(from, to, "\n") : null,
		});
		if (said.html) {
			const chain = props.editor.chain().focus();
			(selected.value ? chain.insertContentAt({ from, to }, said.html) : chain.insertContentAt(from ?? props.editor.state.doc.content.size, said.html)).run();
			prompt.value = "";
			open.value = false;
		} else {
			answer.value = said.answer || "";
		}
	} catch (failed) {
		error.value = failed?.message || __("OneAI could not answer.");
	} finally {
		busy.value = false;
	}
}
</script>
