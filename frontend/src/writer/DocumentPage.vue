<!-- A document in the desk: Suite's writer, opened on the document the route names, under a head that leads back to where the document belongs. -->
<template>
	<div ref="pageEl" class="one-document flex h-full flex-col bg-surface-base">
		<div class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-2 px-4">
			<button class="flex size-6 shrink-0 items-center justify-center [&_svg]:size-full" :title="__('Back')" @click="goBack" v-html="oneMark" />
			<Breadcrumbs v-if="state && !renaming" :items="crumbs">
				<template #prefix="{ item }"><span v-if="item.one" class="font-light">{{ ONE }}</span></template>
			</Breadcrumbs>
			<div v-else-if="state" class="flex min-w-0 items-center">
				<Breadcrumbs :items="parents">
					<template #prefix="{ item }"><span v-if="item.one" class="font-light">{{ ONE }}</span></template>
				</Breadcrumbs>
				<span class="mx-0.5 text-base text-ink-gray-4" aria-hidden="true">/</span>
				<InlineRenameInput v-model="title" editing @submit="rename" @cancel="renaming = false" @blur="rename" />
			</div>
			<span class="text-sm text-ink-gray-5">{{ status }}</span>
			<div class="ml-auto flex items-center gap-2">
				<UsersBar v-if="collaborators.length" :users="collaborators" />
				<Button v-if="asking" variant="ghost" :label="__('Ask OneAI')" @click="showAsk = true">
					<template #prefix><img :src="oneaiMark" class="size-4" alt="" /></template>
				</Button>
				<Button v-if="state?.can_write && settingsDoc.doc.settings.lock" icon="lock" variant="ghost" :tooltip="__('Unlock')" @click="lock(null)" />
				<Dropdown v-if="state" :options="fileMenu" align="end">
					<Button variant="ghost" icon-left="file" :label="__('File')" icon-right="chevron-down" />
				</Dropdown>
			</div>
		</div>
		<div v-if="refused" class="shrink-0 border-b border-outline-gray-2 bg-surface-gray-2 px-4 py-2 text-base text-ink-amber-3">{{ refused }}</div>
		<div v-if="failed" class="flex flex-1 items-center justify-center text-base text-ink-gray-6">{{ failed }}</div>
		<VersionsSidebar
			v-if="state && showVersions"
			:key="versionsKey"
			v-model="versionPreview"
			v-model:show-versions="showVersions"
			:settings="settings"
			:document="settingsDoc"
			:editor="editor"
		/>
		<div v-if="state && rooted" v-show="!showVersions" class="flex min-h-0 w-full flex-1 overflow-hidden">
			<TextEditor
				ref="editorEl"
				:key="state.name"
				v-model:dirty="dirty"
				v-model:show-settings="showSettings"
				:file="file"
				:document="settingsDoc"
				:settings="settings"
				:editable="editable"
			/>
			<WriterSettings v-if="showSettings" v-model="showSettings" :doc-settings="settingsDoc" :global-settings="everywhere" :editable="editable" />
			<TemplateDialog v-if="showTemplates" v-model="showTemplates" :editor="editor" />
			<SaveTemplateDialog v-model="savingTemplate" :document="state.name" :name="state.title" />
			<AskDialog v-if="asking" v-model="showAsk" :document="state.name" :editor="editor" />
		</div>
		<Dialogs />
		<FDialogs />
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, provide, reactive, ref, watch } from "vue";
import { Breadcrumbs, Button, Dialogs, Dropdown } from "frappe-ui";

import { __, call, goTo, goToUrl, listen, me, oneaiMark, oneaiOn, userSettings } from "../kit/desk";
import InlineRenameInput from "../sheet/shim/InlineRenameInput.vue";
import { mark } from "../sheet/shim/mark.js";
import "../sheet/shim/fit.css";
import TextEditor from "./components/TextEditor.vue";
import WriterSettings from "./components/WriterSettings.vue";
import TemplateDialog from "./components/TemplateDialog.vue";
import UsersBar from "./components/UsersBar.vue";
import VersionsSidebar from "./components/VersionsSidebar.vue";
import FDialogs from "./components/FDialogs.vue";
import SaveTemplateDialog from "./shim/SaveTemplateDialog.vue";
import AskDialog from "./shim/AskDialog.vue";
import { getTemplates } from "./shim/resources.js";
import { setWriterRoot } from "./shim/root.js";
import { downloadMD, downloadZippedHTML } from "./utils";

const props = defineProps({ route: { type: Array, default: () => [] }, query: { type: Object, default: () => ({}) } });
const ONE = "One"; // a name, not a word to translate
const oneMark = mark("onedoc");

const state = ref(null);
const failed = ref("");
// Why the record behind this document did not take what was written in it.
const refused = ref("");
const dirty = ref(false);
const saving = ref(false);
const savedOnce = ref(false);
const showSettings = ref(false);
const showTemplates = ref(false);
const savingTemplate = ref(false);
const showVersions = ref(false);
const showAsk = ref(false);
const asking = computed(() => Boolean(state.value?.can_write && oneaiOn()));
const versionPreview = ref(null);
const versionsKey = ref(0);
watch(showVersions, (now) => !now && (versionPreview.value = null));
const renaming = ref(false);
const title = ref("");
const editorEl = ref(null);
const pageEl = ref(null);
// Suite's editor looks itself up in the page; it is drawn once the page knows
// the shadow root it is in.
const rooted = ref(false);
onMounted(() => {
	setWriterRoot(pageEl.value?.getRootNode());
	rooted.value = true;
});
const editor = computed(() => editorEl.value?.editor);
provide("editor", editor);

// What Suite's file and Writer Document resources gave the editor, over
// one_doc/api.py.
const file = reactive({ doc: null });
provide("file", file);
const settingsDoc = reactive({
	doc: { settings: {} },
	isFinished: true,
	onSuccess: () => () => {},
	loading: false,
	saveDoc: {
		error: null,
		submit: ({ data, html }) => {
			saving.value = true;
			return call("onedesk.one_doc.api.save_document", { name: state.value.name, content: data, html })
				.then((said) => {
					refused.value = said?.refused || "";
					settingsDoc.saveDoc.error = null;
					savedOnce.value = true;
					dirty.value = false;
				})
				.catch((err) => {
					settingsDoc.saveDoc.error = err;
					throw err;
				})
				.finally(() => (saving.value = false));
		},
	},
	// A version taken while writing, or one named in the history panel, which
	// is drawn again to list it.
	newVersion: {
		error: null,
		loading: false,
		submit: ({ data, title }) => {
			settingsDoc.newVersion.loading = true;
			return call("onedesk.one_doc.versions.new_version", { name: state.value.name, data, title: title || null })
				.then((made) => {
					settingsDoc.newVersion.error = null;
					if (made && title) versionsKey.value += 1;
					return made;
				})
				.catch((err) => (settingsDoc.newVersion.error = err))
				.finally(() => (settingsDoc.newVersion.loading = false));
		},
	},
	updateSettings: {
		submit: ({ data }) => call("onedesk.one_doc.api.save_settings", { name: state.value.name, settings: data }),
	},
});

const KEY = "writer_settings";
const everywhere = reactive({
	doc: { [KEY]: {} },
	loading: false,
	setValue: { submit: (values) => userSettings.save("Writer Document", KEY, values[KEY]).then(() => (everywhere.doc[KEY] = values[KEY])) },
});

const settings = computed(() => {
	const own = { ...(settingsDoc.doc.settings || {}) };
	for (const [key, value] of Object.entries(own)) if (value === "global") delete own[key];
	return { ...(everywhere.doc[KEY] || {}), ...own };
});

const editable = computed(() => Boolean(state.value?.can_write && !settingsDoc.doc.settings?.lock && editor.value));
const collaborators = computed(() => (editorEl.value?.users || []).filter((one) => one.id !== me()));

// The editor counts its first paint of a saved document as a change, so the
// head says what saving did rather than whether anything is unsaved.
const status = computed(() => {
	if (!state.value) return "";
	if (!state.value.can_write) return __("Read only");
	if (saving.value) return __("Saving…");
	return savedOnce.value ? __("Saved") : "";
});

// The editor names an untitled document from its first line (CoreEditor's
// autorename), through the File.
watch(
	() => file.doc?.file_name,
	(named) => {
		if (named && state.value && named !== state.value.title) state.value.title = title.value = named;
	}
);

async function load(name) {
	failed.value = "";
	try {
		const said = await call("onedesk.one_doc.api.get_document", { name });
		file.doc = { name: said.name, file_name: said.title, write: said.can_write, breadcrumbs: [{ file_name: said.title }] };
		settingsDoc.doc = { name: said.name, content: said.content, ycomments: said.comments, settings: said.settings || {}, owner: said.owner, collab: 1, versions: [] };
		state.value = said;
		title.value = said.title;
		const held = await userSettings.get("Writer Document");
		everywhere.doc[KEY] = held?.[KEY] || {};
		getTemplates.fetch();
	} catch (err) {
		failed.value = err?.message || __("This document could not be opened.");
	}
}
watch(() => props.route[0], (name) => name && load(name), { immediate: true });

// A document made from Word or from a template's HTML has no editor state
// yet: it starts from its HTML, once. Somebody else in it already has,
// and their state arrives over the relay first, so it waits for that.
const SEED_AFTER_MS = 1500;
watch(editor, (now) => {
	if (!now || !state.value || state.value.content || !state.value.html) return;
	setTimeout(() => {
		if (now.isDestroyed || !now.isEmpty) return;
		now.commands.setContent(state.value.html);
		dirty.value = true;
	}, SEED_AFTER_MS);
});

// Where the document belongs, each step a way back: a record's document under
// its doctype and record, any other under its OneCloud folders.
const parents = computed(() => {
	const said = state.value;
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
	{ label: title.value || __("Untitled Document"), onClick: () => state.value?.can_write && (renaming.value = true) },
]);
function goBack() {
	const steps = parents.value;
	steps[steps.length - 1]?.onClick();
}

async function rename(value) {
	renaming.value = false;
	const wanted = (value || "").trim();
	if (!wanted || wanted === state.value.title) return (title.value = state.value.title);
	const said = await call("onedesk.one_doc.api.rename_document", { name: state.value.name, title: wanted });
	state.value.title = title.value = file.doc.file_name = said.title;
}

function lock(value) {
	settingsDoc.doc.settings = { ...settingsDoc.doc.settings, lock: value };
	settingsDoc.updateSettings.submit({ data: JSON.stringify(settingsDoc.doc.settings) });
}

const fileMenu = computed(() => [
	{
		group: __("Export"),
		options: [
			{ label: __("Download as HTML"), icon: "file-code", onClick: () => downloadZippedHTML(editor, title.value, settings.value) },
			{ label: __("Download as Markdown"), icon: "file-text", onClick: () => downloadMD(editor, title.value) },
		],
	},
	{
		group: __("This document"),
		options: [
			...(state.value?.can_write
				? [
						{ label: __("Page Setup"), icon: "settings", onClick: () => (showSettings.value = true) },
						{ label: __("Insert a Template"), icon: "layout-template", onClick: () => (showTemplates.value = true) },
						{ label: __("Rename"), icon: "pencil", onClick: () => (renaming.value = true) },
						settingsDoc.doc.settings?.lock
							? { label: __("Unlock"), icon: "lock-open", onClick: () => lock(null) }
							: { label: __("Lock"), icon: "lock", onClick: () => lock(true) },
					]
				: []),
			{ label: __("Version History"), icon: "history", onClick: () => (showVersions.value = true) },
			{ label: __("Save as Template"), icon: "copy-plus", onClick: () => (savingTemplate.value = true) },
		],
	},
]);

// What OneAI added on a card the reader approved goes in at the end of the
// open copy, which saves it with the rest.
const stopWritten = listen("one_document_written", (said) => {
	if (said?.document !== state.value?.name || !said.html || !editor.value) return;
	editor.value.commands.insertContentAt(editor.value.state.doc.content.size, said.html);
});

onBeforeUnmount(() => {
	stopWritten?.();
	state.value = null;
});
</script>
