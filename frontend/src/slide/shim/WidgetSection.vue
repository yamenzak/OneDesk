<!-- The chosen widget's own settings, in the panel under Frame and Arrange: where it reads from, which fields it shows, a peek at what it shows now, and its kind's settings. Moved from OneDisplay's layout editor (stage 7 of docs/ONEDECK.md). One's own; VENDORED.md. -->
<template>
	<Section :label="kind?.label || __('Widget')">
		<div class="flex flex-col gap-3" @keydown.stop>
			<template v-if="kind?.sources.length">
				<FormControl :model-value="widget.source || ''" :label="__('Source')" type="select" :options="sourceOptions" @update:model-value="setSource" />
				<a class="text-sm text-ink-gray-5 underline" href="/desk/display-source/new" target="_blank">{{ __("New Source") }}</a>
			</template>
			<template v-if="widget.source && kind?.slots.length">
				<span :class="labelClasses">{{ __("Fields Shown") }}</span>
				<div v-for="slot in kind.slots" :key="slot" class="flex flex-col gap-1">
					<FormControl :model-value="mapping[slot] || ''" :label="slots[slot] || slot" type="text" :placeholder="__('Such as {0}', ['{title}'])" @update:model-value="(v) => setSlot(slot, v)" />
					<FormControl v-if="fields.length" :model-value="''" type="select" :options="fieldOptions" @update:model-value="(v) => v && setSlot(slot, `${mapping[slot] || ''}{${v}}`)" />
				</div>
				<div v-if="peeked.length" class="rounded-4 border border-outline-gray-1 p-2">
					<p class="mb-1 text-xs text-ink-gray-5">{{ __("Shows now") }}</p>
					<p v-for="(row, i) in peeked" :key="i" class="truncate text-sm text-ink-gray-7">{{ Object.values(row).filter(Boolean).join(" · ") }}</p>
				</div>
			</template>
			<template v-for="field in kind?.settings || []" :key="field.key">
				<FormControl v-if="field.kind === 'check'" :model-value="Boolean(setting(field))" :label="field.label" type="checkbox" @update:model-value="(v) => set(field.key, v ? 1 : 0)" />
				<FormControl v-else-if="field.kind === 'select'" :model-value="setting(field)" :label="field.label" type="select" :options="field.options" @update:model-value="(v) => set(field.key, v)" />
				<div v-else-if="field.kind === 'long' || field.kind === 'code'" class="flex flex-col gap-1">
					<FormControl :model-value="setting(field)" :label="field.label" type="textarea" :rows="field.kind === 'code' ? 10 : 3" :class="field.kind === 'code' ? 'font-mono' : ''" @update:model-value="(v) => set(field.key, v)" />
					<Button v-if="field.kind === 'code' && oneaiOn()" :label="__('Write with OneAI')" icon-left="lucide-sparkles" :loading="writing" @click="write(field.key)" />
				</div>
				<div v-else-if="field.kind === 'image'" class="flex flex-col gap-1">
					<span class="text-xs text-ink-gray-5">{{ field.label }}</span>
					<img v-if="setting(field)" :src="setting(field)" class="max-h-24 self-start rounded-4" />
					<Button :label="__('Upload')" icon-left="lucide-upload" @click="uploadTo(field.key)" />
				</div>
				<FormControl
					v-else
					:model-value="setting(field)"
					:label="field.label"
					:type="field.kind === 'number' ? 'number' : 'text'"
					:placeholder="field.kind === 'colour' ? __('Brand colour') : ''"
					@update:model-value="(v) => set(field.key, field.kind === 'number' ? Number(v) : v)"
				/>
			</template>
			<FormControl :model-value="widget.shown || 'Always'" :label="__('Shown')" type="select" :options="shownOptions" @update:model-value="(v) => change({ shown: v })" />
			<div v-if="widget.shown === 'Between Times'" class="grid grid-cols-2 gap-2">
				<FormControl :model-value="widget.from_time || ''" :label="__('From')" type="time" @update:model-value="(v) => change({ from_time: v })" />
				<FormControl :model-value="widget.to_time || ''" :label="__('To')" type="time" @update:model-value="(v) => change({ to_time: v })" />
			</div>
		</div>
	</Section>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Button, FormControl } from "frappe-ui";
import Section from "../components/controls/Section.vue";
import { setElementProperty } from "../composables/editProperty";
import { firstEditableElement } from "../stores/element";
import { screen } from "../stores/presentation";
import { labelClasses } from "../utils/constants";
import { __, call, oneaiOn, prompt, upload } from "../../kit/desk";

const API = "onedesk.one_display.layout.";
const slots = { text: __("Words"), title: __("Line"), subtitle: __("Smaller Line"), value: __("Figure"), image: __("Picture"), label: __("Label"), link: __("Address") };
const shownOptions = [
	{ label: __("Always"), value: "Always" },
	{ label: __("Between Times"), value: "Between Times" },
];
const fields = ref([]);
const peeked = ref([]);
const writing = ref(false);

function parsed(value) {
	if (value && typeof value === "object") return value;
	try {
		return JSON.parse(value || "{}") || {};
	} catch {
		return {};
	}
}

const widget = computed(() => firstEditableElement.value?.widget || {});
const kind = computed(() => (screen.value?.types || []).find((one) => one.type === widget.value.widget_type));
const mapping = computed(() => parsed(widget.value.mapping));
const settings = computed(() => parsed(widget.value.settings));
const sourceOptions = computed(() => {
	const kinds = kind.value?.sources || [];
	return [{ label: "", value: "" }, ...(screen.value?.sources || []).filter((s) => kinds.includes(s.kind)).map((s) => ({ label: `${s.name} · ${__(s.kind)}`, value: s.name }))];
});
const fieldOptions = computed(() => [{ label: __("Insert a field"), value: "" }, ...fields.value.map((f) => ({ label: f.label || f.fieldname, value: f.fieldname }))]);

// every change is one undoable step on the element, as any other property is
const change = (values) => setElementProperty("widget", { ...widget.value, ...values });
const setting = (field) => (field.key in settings.value ? settings.value[field.key] : field.default);
const set = (key, value) => change({ settings: { ...settings.value, [key]: value } });
function setSlot(slot, value) {
	change({ mapping: { ...mapping.value, [slot]: value } });
	peek();
}
async function setSource(value) {
	change({ source: value });
	await loadFields();
}
function uploadTo(key) {
	upload(null, null, (file) => set(key, file.file_url), { allow_multiple: false, make_attachments_public: true, restrictions: { allowed_file_types: ["image/*"] } });
}

async function loadFields() {
	fields.value = [];
	peeked.value = [];
	if (!widget.value.source) return;
	fields.value = await call(API + "fields", { source: widget.value.source });
	peek();
}
let peeking = null;
function peek() {
	clearTimeout(peeking);
	peeking = setTimeout(async () => {
		if (!widget.value.source) return;
		const data = await call("onedesk.one_display.sources.peek", {
			source: widget.value.source,
			mapping: JSON.stringify(mapping.value),
			widget_type: widget.value.widget_type,
		});
		peeked.value = (data.rows || []).slice(0, 3);
	}, 400);
}

function write(key) {
	prompt(
		[{ fieldname: "description", fieldtype: "Small Text", label: __("What it shows and does"), reqd: 1 }],
		async ({ description }) => {
			writing.value = true;
			try {
				const code = await call("onedesk.one_display.make.widget", { description, rows: peeked.value.length ? JSON.stringify(peeked.value) : null });
				set(key, code);
			} finally {
				writing.value = false;
			}
		},
		__("Write a Widget"),
		__("Write"),
	);
}

watch(() => firstEditableElement.value?.id, loadFields, { immediate: true });
</script>
