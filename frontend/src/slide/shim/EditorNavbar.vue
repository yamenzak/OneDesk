<!-- Suite's editor head, drawn as One's: the way back to where the presentation belongs, its title, whether it is saved, and Theme, Export and Present (Suite's EditorNavbar.vue, which this stands in for). -->
<template>
	<div data-tour="oneslide-head" class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-2 bg-surface-base px-4">
		<button class="flex size-6 shrink-0 items-center justify-center [&_svg]:size-full" :title="__('Back')" @click="goBack" v-html="oneMark" />
		<Breadcrumbs class="min-w-0 overflow-hidden [&_:is(a,button):has(>.one-crumb-mark)]:[direction:ltr]" v-if="!renaming" :items="crumbs">
			<template #prefix="{ item }"><span v-if="item.one" class="one-crumb-mark font-light">{{ ONE }}</span></template>
		</Breadcrumbs>
		<div v-else class="flex min-w-0 items-center">
			<Breadcrumbs class="[&_:is(a,button):has(>.one-crumb-mark)]:[direction:ltr]" :items="parents">
				<template #prefix="{ item }"><span v-if="item.one" class="one-crumb-mark font-light">{{ ONE }}</span></template>
			</Breadcrumbs>
			<span class="mx-0.5 text-base text-ink-gray-4" aria-hidden="true">/</span>
			<InlineRenameInput v-model="title" editing @submit="rename" @cancel="renaming = false" @blur="rename" />
		</div>
		<span class="text-sm text-ink-gray-5 max-md:hidden">{{ making || status }}</span>
		<div class="ml-auto flex shrink-0 items-center gap-2">
			<Button v-if="!inReadonlyMode && screen" variant="ghost" icon-left="lucide-layout-template" :label="__('Templates')" @click="showTemplates = true" />
			<Button v-if="!inReadonlyMode && screen" variant="ghost" icon-left="lucide-layout-dashboard" :label="__('Add a Widget')" @click="showWidgets = true" />
			<Dropdown v-if="!inReadonlyMode && presentationDoc && oneaiOn() && !masterOf" :options="aiMenu" align="end">
				<Button variant="ghost" :label="ONEAI" icon-right="lucide-chevron-down" :loading="!!making">
					<template #prefix><img :src="oneaiMark" class="size-4" alt="" /></template>
				</Button>
			</Dropdown>
			<Button v-if="!inReadonlyMode && presentationDoc && !screen && !masterOf" class="max-md:hidden" variant="ghost" icon-left="lucide-palette" :label="__('Theme')" @click="emit('performDropdownAction', 'updateTheme')" />
			<!-- a screen's: its data and guides, since it is one slide and no presentation of its own -->
			<Dropdown v-if="presentationDoc" :options="fileMenu" align="end">
				<Button variant="ghost" icon-left="lucide-file" :label="__('File')" icon-right="lucide-chevron-down" />
			</Dropdown>
			<PresentButton v-if="presentationDoc && !screen && !masterOf" @start="(options) => emit('startSlideShow', options)" />
			<Button v-if="masterOf" variant="solid" icon-left="lucide-check" :label="__('Done')" @click="leaveMaster" />
			<Button v-if="screen" variant="solid" icon-left="lucide-monitor-play" :label="__('Preview')" @click="openTab(`/tv?collection=${encodeURIComponent(screen.name)}`)" />
		</div>
		<SlideCamera ref="camera" />
		<VersionsDialog v-if="presentationDoc" v-model="showVersions" :name="presentationDoc.name" :writable="!inReadonlyMode" @restored="reload" />
		<ViewsDialog v-if="presentationDoc" v-model="showViews" :name="presentationDoc.name" />
		<WidgetGallery v-if="screen" v-model:open="showWidgets" @add="addWidget" />
		<ScreenTemplates v-if="screen && !inReadonlyMode" v-model:open="showTemplates" />
		<DataDialog v-if="presentationDoc" v-model="showData" :record="presentationDoc.record" :readonly="inReadonlyMode" :screen="!!screen" />
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, ref, watch } from "vue";
import { Breadcrumbs, Button, Dropdown } from "frappe-ui";

import { __, aiSees, alert, askOneAI, call, confirm, goTo, goToUrl, listen, onedesk, oneaiMark, oneaiOn, openTab, prompt, reloadPage, requires } from "../../kit/desk";
import InlineRenameInput from "../../sheet/shim/InlineRenameInput.vue";
import { mark } from "../../sheet/shim/mark.js";
import PresentButton from "../components/PresentButton.vue";
import { initPresentationDoc, presentationDoc, screen, updatePresentationTitle } from "../stores/presentation";
import { addWidget } from "./screen.js";
import { frame, sizes } from "./frame.js";
import { addMarginGuides, clearGuides, guides, rulersShown, toggleRulers } from "./guides.js";
import { fieldElement, masterOf } from "./master.js";
import { addElementCommand, batchCommand } from "../stores/commands";
import { addMediaElement } from "../stores/element";
import { changeSlide, currentSlide, getNewSlide, insertSlide, slideIndex, slides } from "../stores/slide";
import { commandHistory } from "../stores/historyMeta";
import { dirty, isSaving, saveFailed, saveWithoutDelay } from "../stores/saving";
import SlideCamera from "./SlideCamera.vue";
import VersionsDialog from "./VersionsDialog.vue";
import DataDialog from "./DataDialog.vue";
import WidgetGallery from "./WidgetGallery.vue";
import ScreenTemplates from "./ScreenTemplates.vue";
import ViewsDialog from "./ViewsDialog.vue";
import { sources } from "./data.js";

const emit = defineEmits(["startSlideShow", "performDropdownAction"]);
const ONE = "One"; // a name, not a word to translate
const ONEAI = "OneAI"; // a name too
// a screen's editor belongs to OneDisplay, a presentation's to OneSlide
const oneMark = computed(() => mark(screen.value ? "onedisplay" : "oneslide"));
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
	{ label: title.value || __("Untitled Presentation"), onClick: () => !inReadonlyMode.value && !masterOf.value && (renaming.value = true) },
]);

function goBack() {
	const steps = parents.value;
	steps[steps.length - 1]?.onClick();
}

const camera = ref(null);
const showVersions = ref(false);
const showData = ref(false);
const showViews = ref(false);

async function share() {
	const doc = presentationDoc.value;
	await requires(onedesk().cloud_assets);
	onedesk().cloud.share({ id: doc.file, name: doc.title, record: doc.record });
}
const printing = ref("");

const fileMenu = computed(() => [
	// the master: its fields to put on, and the way back
	...(masterOf.value
		? [
				{
					group: __("Master"),
					options: [
						...(inReadonlyMode.value ? [] : [{ label: __("Add Slide Number"), icon: "lucide-hash", onClick: () => addField("number") }]),
						...(inReadonlyMode.value ? [] : [{ label: __("Add Date"), icon: "lucide-calendar", onClick: () => addField("date") }]),
						{ label: __("Version History"), icon: "lucide-history", onClick: () => (showVersions.value = true) },
					],
				},
			]
		: []),
	...(masterOf.value || screen.value ? [] : [{
		group: __("This presentation"),
		options: [
			// OneCloud's own: people who may view or edit it, and links for anyone else
			...(presentationDoc.value?.file ? [{ label: __("Share…"), icon: "lucide-user-plus", onClick: share }] : []),
			{ label: printing.value || __("Export as PDF"), icon: "lucide-file-down", onClick: () => exportPdf(false) },
			...(printing.value ? [] : [{ label: __("Export as PDF with Notes"), icon: "lucide-notebook-text", onClick: () => exportPdf(true) }]),
			...(printing.value ? [] : [{ label: __("Export as PowerPoint"), icon: "lucide-presentation", onClick: exportPowerPoint }]),
			{ label: __("Version History"), icon: "lucide-history", onClick: () => (showVersions.value = true) },
			...(inReadonlyMode.value ? [] : [{ label: __("Views"), icon: "lucide-eye", onClick: () => (showViews.value = true) }]),
			...(presentationDoc.value?.can_template ? [{ label: __("Save as Template"), icon: "lucide-copy-plus", onClick: saveAsTemplate }] : []),
			...(inReadonlyMode.value ? [] : [{ label: __("Rename"), icon: "lucide-pencil", onClick: () => (renaming.value = true) }]),
			...(inReadonlyMode.value ? [] : [{ label: __("Slide Size"), icon: "lucide-ratio", onClick: slideSize }]),
			...(inReadonlyMode.value || screen.value ? [] : [{ label: __("Edit Master"), icon: "lucide-layers", onClick: openMaster }]),
			...(inReadonlyMode.value || !slides.value.some((one) => one.layout) ? [] : [{ label: __("Restyle from Layouts"), icon: "lucide-paintbrush", onClick: restyle }]),
		],
	}]),
	...(masterOf.value ? [] : [{
		group: __("Data"),
		options: [
			{ label: __("Data from Records"), icon: "lucide-database", onClick: () => (showData.value = true) },
			...(inReadonlyMode.value || !sources.value.length || screen.value ? [] : [{ label: __("Freeze Data"), icon: "lucide-snowflake", onClick: freezeData }]),
			...(!screen.value && sources.value.some((one) => one.kind === "this" && one.doctype) ? [{ label: __("Make One for Each…"), icon: "lucide-copy", onClick: makeForEach }] : []),
		],
	}]),
	{
		group: __("Guides"),
		options: [
			{ label: rulersShown.value ? __("Hide Rulers and Guides") : __("Show Rulers and Guides"), icon: "lucide-ruler", onClick: toggleRulers },
			...(inReadonlyMode.value ? [] : [{ label: __("Add Margin Guides"), icon: "lucide-frame", onClick: addMarginGuides }]),
			...(inReadonlyMode.value || !guides.value.length ? [] : [{ label: __("Clear Guides"), icon: "lucide-eraser", onClick: clearGuides }]),
		],
	},
]);

// The master opens in this same editor, on a presentation of its own
// (one_slide/master.py); Done comes back.
async function openMaster() {
	await saveWithoutDelay();
	const name = await call("onedesk.one_slide.master.edit", { name: presentationDoc.value.name });
	goToUrl(`/desk/presentation/${name}`);
}

async function leaveMaster() {
	await saveWithoutDelay();
	goToUrl(`/desk/presentation/${masterOf.value}`);
}

function addField(field) {
	const slide = currentSlide.value;
	if (!slide) return;
	const element = { ...fieldElement(field, frame), zIndex: Math.max(0, ...slide.elements.map((one) => one.zIndex || 0)) + 1 };
	commandHistory.execute(batchCommand({ slideId: slide.clientId, elementIds: [element.id], commands: [addElementCommand({ slideId: slide.clientId, element })] }));
}

// Every slide that came from a layout takes its layout's look again, keeping
// its words (one_slide/layouts.py); what it was is a version.
async function restyle() {
	await saveWithoutDelay();
	const { restyled } = await call("onedesk.one_slide.layouts.restyle", { name: presentationDoc.value.name });
	if (!restyled) return alert(__("Every slide already looks like its layout."));
	reloadPage();
}

// Every slide made another size, its contents redrawn to fit (one_slide/resize.py).
// The editor's canvas is laid out for one size, so it opens again at the new one.
function slideSize() {
	const offered = sizes();
	const now = offered.find((one) => one.w === frame.w && one.h === frame.h);
	prompt(
		[
			{
				fieldname: "size",
				fieldtype: "Select",
				label: __("Size"),
				options: [...offered.map((one) => ({ label: one.label, value: one.key })), { label: __("Custom"), value: "custom" }],
				default: now ? now.key : "custom",
			},
			{ fieldname: "width", fieldtype: "Int", label: __("Width"), default: frame.w, depends_on: "eval:doc.size=='custom'" },
			{ fieldname: "height", fieldtype: "Int", label: __("Height"), default: frame.h, depends_on: "eval:doc.size=='custom'" },
		],
		async ({ size, width, height }) => {
			const preset = offered.find((one) => one.key === size);
			await saveWithoutDelay();
			await call("onedesk.one_slide.resize.resize", { name: presentationDoc.value.name, width: preset ? preset.w : width, height: preset ? preset.h : height });
			reloadPage();
		},
		__("Slide Size"),
		__("Change")
	);
}

// Every slide photographed as the editor draws it, then made a PDF beside
// the presentation in OneCloud, and opened: the slides alone, or each above
// its speaker notes (one_slide/paper.py).
async function exportPdf(notes) {
	if (printing.value) return;
	printing.value = __("Preparing the PDF…");
	try {
		const pictures = await camera.value.shoot(slides.value, (done, all) => (printing.value = __("Drawing slide {0} of {1}…", [done, all])));
		await saveWithoutDelay();
		const made = await call("onedesk.one_slide.paper.pdf", { name: presentationDoc.value.name, pictures: JSON.stringify(pictures), notes: notes ? 1 : 0 });
		alert(__("Saved {0} to OneCloud.", [made.file_name]));
		openTab(made.url);
	} finally {
		printing.value = "";
	}
}

// The presentation as a .pptx beside it, made of PowerPoint's own pieces
// (one_slide/powerpoint.py); a slide with something PowerPoint has nothing like is named.
async function exportPowerPoint() {
	if (printing.value) return;
	printing.value = __("Preparing the PowerPoint file…");
	try {
		await saveWithoutDelay();
		const made = await call("onedesk.one_slide.powerpoint.export", { name: presentationDoc.value.name });
		alert(made.lost.length ? __("Saved {0} to OneCloud. Slides {1} lost an effect PowerPoint does not have.", [made.file_name, made.lost.join(", ")]) : __("Saved {0} to OneCloud.", [made.file_name]), made.lost.length ? "yellow" : "green");
		openTab(made.url);
	} finally {
		printing.value = "";
	}
}

// Every chip written in as it reads now, for good (one_slide/data.py freeze);
// what it was is kept as a version.
function freezeData() {
	confirm(__("Write in what the data says now? The slides stop following the records. What they were is kept in Version History."), async () => {
		await saveWithoutDelay();
		await call("onedesk.one_slide.data.freeze", { name: presentationDoc.value.name });
		await reload();
		alert(__("The data is written in."));
	});
}

// A copy of this presentation filed on each record picked, made in the
// background; each reads its own record as `this` (one_slide/data.py for_each).
function makeForEach() {
	const doctype = sources.value.find((one) => one.kind === "this").doctype;
	prompt(
		[
			{
				fieldname: "names",
				fieldtype: "MultiSelectList",
				label: __("Records"),
				reqd: 1,
				get_data: (txt) => call("frappe.desk.search.search_link", { doctype, txt, page_length: 20 }),
			},
		],
		async ({ names }) => {
			await saveWithoutDelay();
			const { queued } = await call("onedesk.one_slide.data.for_each", { name: presentationDoc.value.name, names });
			alert(__("Making {0} presentations. You will be told when they are filed.", [queued]));
		},
		__("Make One for Each {0}", [__(doctype)]),
		__("Make")
	);
}

const unheard = listen("one_slide_for_each", ({ made, doctype }) => alert(__("{0} presentations filed, one on each {1}.", [made, __(doctype)]), "green"));
onBeforeUnmount(unheard);

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

// What OneAI makes here (onedesk/one_slide/ai.py): a slide after this one, a
// picture on this one, or a video that arrives later on a slide of its own.
const making = ref("");
const aiMenu = computed(() => [
	{
		group: ONEAI,
		options: [
			// a screen has one slide: OneAI adds to it, never a slide after it
			...(screen.value ? [] : [{ label: __("Design a Slide"), icon: "lucide-layout-template", onClick: designSlide }]),
			{ label: __("Make a Picture"), icon: "lucide-image", onClick: makePicture },
			...(screen.value ? [] : [{ label: __("Make a Video"), icon: "lucide-film", onClick: makeVideo }]),
		],
	},
	// in OneAI's panel, as cards to approve (one_slide/ai.py draft_deck, write_slide, remake_slide)
	...(screen.value ? [] : [{
		group: __("In the OneAI Panel"),
		options: [
			{ label: __("Write a Whole Deck"), icon: "lucide-presentation", onClick: writeDeck },
			{ label: __("Rewrite This Slide"), icon: "lucide-pencil-line", onClick: () => askOneAI(__("Rewrite this slide so it reads better.")) },
			{ label: __("Shorten This Slide"), icon: "lucide-scissors", onClick: () => askOneAI(__("Shorten this slide's words.")) },
			{ label: __("Translate This Slide"), icon: "lucide-languages", onClick: translateSlide },
			{ label: __("Make This Slide a Timeline"), icon: "lucide-milestone", onClick: () => askOneAI(__("Make this slide a timeline.")) },
		],
	}]),
]);

function writeDeck() {
	described(__("Write a Whole Deck"), __("Ask OneAI"), (description) => askOneAI(__("Write a whole deck in this presentation: {0}", [description])));
}

function translateSlide() {
	prompt([{ fieldname: "language", fieldtype: "Link", options: "Language", label: __("Into"), reqd: 1 }], ({ language }) => askOneAI(__("Translate this slide into {0}.", [language])), __("Translate This Slide"), __("Ask OneAI"));
}

// the slide that is open, so "this slide" in OneAI's panel means it
watch(
	() => [presentationDoc.value?.name, currentSlide.value?.clientId],
	([presentation, slide]) => aiSees(presentation ? { page: "presentation", presentation, slide } : null),
	{ immediate: true },
);
onBeforeUnmount(() => aiSees(null));

// a card approved in OneAI's panel changed the slides: open them as they are now
const unwritten = listen("one_slide_written", (said) => said?.presentation === presentationDoc.value?.name && reload());
onBeforeUnmount(unwritten);
const showWidgets = ref(false);
// an empty screen opens on its templates, which is where most start
const showTemplates = ref(false);
let looked = false;
watch(
	() => screen.value && currentSlide.value,
	(slide) => {
		if (!slide || looked) return;
		looked = true;
		if (!inReadonlyMode.value && !slide.elements.length) showTemplates.value = true;
	},
	{ immediate: true }
);

function described(title, label, done) {
	prompt([{ fieldname: "description", fieldtype: "Small Text", label: __("Describe It"), reqd: 1 }], ({ description }) => done(description), title, label);
}

async function asking(saying, method, description) {
	making.value = saying;
	try {
		return await call(method, { name: presentationDoc.value.name, description });
	} finally {
		making.value = "";
	}
}

function designSlide() {
	described(__("Design a Slide"), __("Design"), async (description) => {
		const made = await asking(__("OneAI is designing the slide…"), "onedesk.one_slide.ai.design", description);
		const at = slideIndex.value;
		insertSlide(getNewSlide(false, { background: made.background, elements: made.elements }), at);
		changeSlide(at + 1);
	});
}

function makePicture() {
	const slide = currentSlide.value;
	described(__("Make a Picture"), __("Make"), async (description) => {
		const made = await asking(__("OneAI is making the picture…"), "onedesk.one_slide.ai.picture", description);
		await addMediaElement(made, "image", slide);
	});
}

function makeVideo() {
	described(__("Make a Video"), __("Make"), async (description) => {
		await saveWithoutDelay();
		await asking(__("OneAI is starting the video…"), "onedesk.one_slide.ai.video", description);
		alert(__("OneAI is making the video. It takes a few minutes; it will be on a new slide at the end, and you will be told."));
	});
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
