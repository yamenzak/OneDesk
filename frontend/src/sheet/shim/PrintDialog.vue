<!-- Print a sheet or the whole workbook under the letter head (one_sheet/paper.py): open it to print, and keep it beside the workbook or, for a record's workbook, on the record. -->
<template>
	<Dialog v-model:open="open" :title="__('Print')" size="md">
		<template #default>
			<div class="flex flex-col gap-3">
				<FormControl v-model="what" type="select" :label="__('Sheets')" :options="whats" />
				<FormControl v-model="turn" type="select" :label="__('Orientation')" :options="turns" />
				<FormControl v-model="fit" type="checkbox" :label="__('Fit to page width')" />
				<FormControl v-model="gridlines" type="checkbox" :label="__('Gridlines')" />
				<FormControl v-model="head" type="select" :label="__('Letter head')" :options="heads" />
				<p v-if="kept" class="text-sm text-ink-gray-5"><Branded :text="kept" /></p>
				<p v-if="error" class="text-sm text-ink-red-4">{{ error }}</p>
			</div>
		</template>
		<template #actions>
			<div class="flex flex-col gap-2">
				<Button variant="solid" class="w-full" :loading="busy === 'print'" :disabled="!!busy" @click="print">{{ __("Print") }}</Button>
				<Button v-if="!bound" class="w-full" :loading="busy === 'cloud'" :disabled="!!busy" @click="keep('cloud')"><Branded :text="__('Save PDF to {0}', [name('one_cloud')])" /></Button>
				<Button v-else class="w-full" :loading="busy === 'record'" :disabled="!!busy" @click="keep('record')">{{ __("Attach PDF to {0}", [bound.name]) }}</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog, FormControl } from "frappe-ui";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import Branded from "../../kit/Branded.vue";
import { __, csrf, followList, openTab, name } from "../../kit/desk";
import { call } from "../utils/api.js";

const props = defineProps({
	modelValue: Boolean,
	workbook: { type: String, default: "" },
	current: { type: String, default: "" },
	count: { type: Number, default: 1 },
	bound: { type: Object, default: null },
	build: { type: Function, required: true },
});
const emit = defineEmits(["update:modelValue"]);
const open = computed({ get: () => props.modelValue, set: (said) => emit("update:modelValue", said) });
const what = ref("sheet");
const turn = ref("portrait");
const fit = ref(true);
const gridlines = ref(true);
const head = ref("");
const held = ref([]);
const busy = ref("");
const error = ref("");
const kept = ref("");

const whats = computed(() => [
	{ label: __("This sheet ({0})", [props.current]), value: "sheet" },
	...(props.count > 1 ? [{ label: __("All sheets"), value: "all" }] : []),
]);
// The workspace's letter heads, the default first and chosen; with none,
// the one paper.py draws from the company.
const heads = computed(() => [
	...(held.value.length ? held.value.map((one) => ({ label: one.is_default ? __("{0} (default)", [one.name]) : one.name, value: one.name })) : [{ label: __("Company details"), value: "" }]),
	{ label: __("None"), value: "none" },
]);

const turns = [
	{ label: __("Portrait"), value: "portrait" },
	{ label: __("Landscape"), value: "landscape" },
];

// Wider than a portrait page (paper.py's room: 180mm, 884px there), it
// starts on its side.
const PORTRAIT = 884;

let stop = null;

watch(open, (now) => {
	if (now) {
		error.value = "";
		kept.value = "";
		const [drawn] = props.build(false);
		const hidden = new Set(drawn?.hidden_cols || []);
		let wide = 0;
		for (let col = 0; col < (drawn?.size?.[1] || 0); col++) if (!hidden.has(col)) wide += drawn.widths[col] ?? 100;
		turn.value = wide > PORTRAIT ? "landscape" : "portrait";
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
	return {
		name: props.workbook,
		sheets: JSON.stringify(props.build(what.value === "all")),
		landscape: turn.value === "landscape" ? 1 : 0,
		fit: fit.value ? 1 : 0,
		gridlines: gridlines.value ? 1 : 0,
		letter_head: head.value,
		keep,
	};
}

// The PDF opens in a tab of its own, where the browser prints it. The tab is
// opened before the PDF is asked for, so it isn't blocked as a popup.
async function print() {
	busy.value = "print";
	error.value = "";
	const tab = openTab();
	try {
		const answer = await fetch("/api/method/onedesk.one_sheet.paper.pdf", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": csrf(), "Content-Type": "application/x-www-form-urlencoded" },
			body: new URLSearchParams(args()),
		});
		if (!answer.ok || !(answer.headers.get("content-type") || "").includes("pdf")) throw new Error(await refused(answer));
		const url = URL.createObjectURL(await answer.blob());
		if (tab) tab.location.href = url;
		else Object.assign(document.createElement("a"), { href: url, target: "_blank" }).click();
		open.value = false;
	} catch (failed) {
		tab?.close();
		error.value = failed?.message || __("Could not print the sheet.");
	} finally {
		busy.value = "";
	}
}

async function refused(answer) {
	try {
		const said = await answer.json();
		const first = JSON.parse(JSON.parse(said._server_messages || "[]")[0] || "{}");
		return first.message || __("Could not print the sheet.");
	} catch {
		return __("Could not print the sheet.");
	}
}

async function keep(where) {
	busy.value = where;
	error.value = "";
	kept.value = "";
	try {
		const made = await call("onedesk.one_sheet.paper.pdf", args(where));
		kept.value = where === "record"
			? __("{0} attached to {1}.", [made.name, props.bound.name])
			: __("{0} saved to {1}, in the same folder as this workbook.", [made.name, name("one_cloud")]);
	} catch (failed) {
		error.value = failed?.message || __("Could not save the PDF.");
	} finally {
		busy.value = "";
	}
}
</script>
