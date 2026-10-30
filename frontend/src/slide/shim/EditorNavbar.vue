<!-- Suite's editor head, drawn as One's: the way back to where the presentation belongs, its title, whether it is saved, and Theme, Export and Present (Suite's EditorNavbar.vue, which this stands in for). -->
<template>
	<div class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-2 bg-surface-base px-4">
		<button class="flex size-6 shrink-0 items-center justify-center [&_svg]:size-full" :title="__('Back')" @click="goBack" v-html="oneMark" />
		<Breadcrumbs v-if="!renaming" :items="crumbs">
			<template #prefix="{ item }"><span v-if="item.one" class="font-light">{{ ONE }}</span></template>
		</Breadcrumbs>
		<div v-else class="flex min-w-0 items-center">
			<Breadcrumbs :items="parents">
				<template #prefix="{ item }"><span v-if="item.one" class="font-light">{{ ONE }}</span></template>
			</Breadcrumbs>
			<span class="mx-0.5 text-base text-ink-gray-4" aria-hidden="true">/</span>
			<InlineRenameInput v-model="title" editing @submit="rename" @cancel="renaming = false" @blur="rename" />
		</div>
		<span class="text-sm text-ink-gray-5">{{ status }}</span>
		<div class="ml-auto flex items-center gap-2">
			<Button v-if="!inReadonlyMode && presentationDoc" variant="ghost" icon-left="lucide-palette" :label="__('Theme')" @click="emit('performDropdownAction', 'updateTheme')" />
			<Dropdown v-if="presentationDoc" :options="fileMenu" align="end">
				<Button variant="ghost" icon-left="lucide-file" :label="__('File')" icon-right="lucide-chevron-down" />
			</Dropdown>
			<PresentButton v-if="presentationDoc" @start="(options) => emit('startSlideShow', options)" />
		</div>
		<SlideCamera ref="camera" />
		<VersionsDialog v-if="presentationDoc" v-model="showVersions" :name="presentationDoc.name" :writable="!inReadonlyMode" @restored="reload" />
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue";
import { Breadcrumbs, Button, Dropdown } from "frappe-ui";

import { __, alert, call, goTo, goToUrl, openTab, prompt } from "../../kit/desk";
import InlineRenameInput from "../../sheet/shim/InlineRenameInput.vue";
import { mark } from "../../sheet/shim/mark.js";
import PresentButton from "../components/PresentButton.vue";
import { initPresentationDoc, presentationDoc, updatePresentationTitle } from "../stores/presentation";
import { slides } from "../stores/slide";
import { commandHistory } from "../stores/historyMeta";
import { dirty, isSaving, saveFailed, saveWithoutDelay } from "../stores/saving";
import SlideCamera from "./SlideCamera.vue";
import VersionsDialog from "./VersionsDialog.vue";

const emit = defineEmits(["startSlideShow", "performDropdownAction"]);
const ONE = "One"; // a name, not a word to translate
const oneMark = mark("oneslide");
const inReadonlyMode = inject("inReadonlyMode", ref(false));
const renaming = ref(false);
const title = ref("");
const savedOnce = ref(false);

watch(
	() => presentationDoc.value?.title,
	(now) => (title.value = now || ""),
	{ immediate: true }
);
watch(isSaving, (now, was) => was && !now && !saveFailed.value && (savedOnce.value = true));

const status = computed(() => {
	if (!presentationDoc.value) return "";
	if (inReadonlyMode.value) return __("Read only");
	if (saveFailed.value) return __("Not saved");
	if (isSaving.value || dirty.value) return __("Saving…");
	return savedOnce.value ? __("Saved") : "";
});

// Where the presentation belongs, each step a way back: a record's under its
// doctype and record, any other under its OneCloud folders.
const parents = computed(() => {
	const said = presentationDoc.value;
	if (!said) return [];
	if (said.record) {
		return [
			{ label: __(said.record.doctype), onClick: () => goTo("List", said.record.doctype) },
			{ label: said.record.name, onClick: () => goTo("Form", said.record.doctype, said.record.name) },
		];
	}
	const folders = said.trail?.length ? said.trail : [{ id: "", name: "OneCloud" }];
	return folders.map((one, at) => ({
		...(at ? { label: one.name } : { label: "Cloud", one: true }),
		onClick: () => goToUrl(one.id ? `/desk/onecloud?node=${encodeURIComponent(one.id)}` : "/desk/onecloud"),
	}));
});
const crumbs = computed(() => [
	...parents.value,
	{ label: title.value || __("Untitled Presentation"), onClick: () => !inReadonlyMode.value && (renaming.value = true) },
]);

function goBack() {
	const steps = parents.value;
	steps[steps.length - 1]?.onClick();
}

const camera = ref(null);
const showVersions = ref(false);
const printing = ref("");

const fileMenu = computed(() => [
	{
		group: __("This presentation"),
		options: [
			{ label: printing.value || __("Export as PDF"), icon: "lucide-file-down", onClick: exportPdf },
			{ label: __("Version History"), icon: "lucide-history", onClick: () => (showVersions.value = true) },
			{ label: __("Save as Template"), icon: "lucide-copy-plus", onClick: saveAsTemplate },
			...(inReadonlyMode.value ? [] : [{ label: __("Rename"), icon: "lucide-pencil", onClick: () => (renaming.value = true) }]),
		],
	},
]);

// Every slide photographed as the editor draws it, then made a PDF beside
// the presentation in OneCloud, and opened.
async function exportPdf() {
	if (printing.value) return;
	printing.value = __("Preparing the PDF…");
	try {
		const pictures = await camera.value.shoot(slides.value, (done, all) => (printing.value = __("Drawing slide {0} of {1}…", [done, all])));
		const made = await call("onedesk.one_slide.paper.pdf", { name: presentationDoc.value.name, pictures: JSON.stringify(pictures) });
		alert(__("Saved {0} to OneCloud.", [made.file_name]));
		openTab(made.url);
	} finally {
		printing.value = "";
	}
}

function saveAsTemplate() {
	prompt(
		[{ fieldname: "title", fieldtype: "Data", label: __("Template Name"), reqd: 1, default: presentationDoc.value.title }],
		async ({ title }) => {
			const made = await call("onedesk.one_slide.templates.save_as", { name: presentationDoc.value.name, title });
			alert(__("{0} is in Presentation Templates.", [made.title]));
		},
		__("Save as Template"),
		__("Save")
	);
}

// Going back to a version: what is unsaved goes first, then the presentation
// is opened again as the server now has it.
async function reload() {
	await saveWithoutDelay();
	await initPresentationDoc(presentationDoc.value.name, false);
	commandHistory.clearHistory();
}

async function rename(value) {
	renaming.value = false;
	const wanted = (value || "").trim();
	const was = presentationDoc.value?.title;
	if (!wanted || wanted === was) return (title.value = was || "");
	await updatePresentationTitle(presentationDoc.value.name, wanted);
}
</script>
