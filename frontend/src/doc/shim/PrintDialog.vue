<!-- Print a document under the letter head (one_doc/paper.py): open it to print, and keep it beside the document or on the record it is on. -->
<template>
	<Dialog v-model:open="open" :title="__('Print')" size="md">
		<template #default>
			<div class="flex flex-col gap-3">
				<FormControl v-model="head" type="select" :label="__('Letter head')" :options="heads" />
				<FormControl v-model="turn" type="select" :label="__('Orientation')" :options="turns" />
				<p v-if="record" class="text-sm text-ink-gray-5">{{ __("The fields in this document are filled from {0}.", [record.name]) }}</p>
				<p v-if="kept" class="text-sm text-ink-gray-5"><Branded :text="kept" /></p>
				<p v-if="error" class="text-sm text-ink-red-4">{{ error }}</p>
			</div>
		</template>
		<template #actions>
			<div class="flex flex-col gap-2">
				<Button variant="solid" class="w-full" :loading="busy === 'print'" :disabled="!!busy" @click="print">{{ __("Print") }}</Button>
				<Button v-if="record" class="w-full" :loading="busy === 'record'" :disabled="!!busy" @click="keep('record')">{{ __("Attach PDF to {0}", [record.name]) }}</Button>
				<Button v-else class="w-full" :loading="busy === 'cloud'" :disabled="!!busy" @click="keep('cloud')"><Branded :text="__('Save PDF to {0}', [name('one_cloud')])" /></Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog, FormControl } from "frappe-ui";
import { computed, onBeforeUnmount, ref, watch } from "vue";

import Branded from "../../kit/Branded.vue";
import { __, call, csrf, followList, openTab, name } from "../../kit/desk";

const props = defineProps({
	modelValue: Boolean,
	document: { type: String, default: "" },
	record: { type: Object, default: null },
});
const emit = defineEmits(["update:modelValue"]);
const open = computed({ get: () => props.modelValue, set: (said) => emit("update:modelValue", said) });
const head = ref("");
const turn = ref("portrait");
const held = ref([]);
const busy = ref("");
const error = ref("");
const kept = ref("");

// The workspace's letter heads, the default first and chosen; with none,
// the one drawn from the company.
const heads = computed(() => [
	...(held.value.length ? held.value.map((one) => ({ label: one.is_default ? __("{0} (default)", [one.name]) : one.name, value: one.name })) : [{ label: __("Company details"), value: "" }]),
	{ label: __("None"), value: "none" },
]);
const turns = [
	{ label: __("Portrait"), value: "portrait" },
	{ label: __("Landscape"), value: "landscape" },
];

let stop = null;
watch(open, (now) => {
	if (now) {
		error.value = kept.value = "";
		loadHeads();
		stop = followList("Letter Head", loadHeads);
	} else {
		stop?.();
		stop = null;
	}
});
onBeforeUnmount(() => stop?.());

function loadHeads() {
	call("onedesk.one_sheet.paper.letter_heads").then((found) => {
		held.value = found || [];
		if (!heads.value.some((one) => one.value === head.value)) head.value = heads.value[0].value;
	});
}

function args(keep = "") {
	return { name: props.document, letter_head: head.value, landscape: turn.value === "landscape" ? 1 : 0, keep };
}

// The PDF opens in a tab of its own, where the browser prints it; the tab is
// opened first so it isn't blocked as a popup.
async function print() {
	busy.value = "print";
	error.value = "";
	const tab = openTab();
	try {
		const answer = await fetch("/api/method/onedesk.one_doc.paper.pdf", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": csrf(), "Content-Type": "application/x-www-form-urlencoded" },
			body: new URLSearchParams(args()),
		});
		if (!answer.ok || !(answer.headers.get("content-type") || "").includes("pdf")) throw new Error(__("Could not print the document."));
		const url = URL.createObjectURL(await answer.blob());
		if (tab) tab.location.href = url;
		else Object.assign(document.createElement("a"), { href: url, target: "_blank" }).click();
		open.value = false;
	} catch (failed) {
		tab?.close();
		error.value = failed?.message || __("Could not print the document.");
	} finally {
		busy.value = "";
	}
}

async function keep(where) {
	busy.value = where;
	error.value = kept.value = "";
	try {
		const made = await call("onedesk.one_doc.paper.pdf", args(where));
		kept.value = where === "record" ? __("{0} attached to {1}.", [made.name, props.record.name]) : __("{0} saved to {1}, in the same folder as this document.", [made.name, name("one_cloud")]);
	} catch (failed) {
		error.value = failed?.message || __("Could not save the PDF.");
	} finally {
		busy.value = "";
	}
}
</script>
