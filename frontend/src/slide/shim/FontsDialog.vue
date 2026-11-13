<!-- Adding a font to the workspace (one_deck/fonts.py): a file of the
     company's own, or a family from Google's catalogue while the workspace
     has Fonts from Google on. One's own; VENDORED.md. -->
<template>
	<Dialog v-model:open="open" :title="__('Add a Font')" size="lg">
			<div class="flex flex-col gap-4" @keydown.stop>
				<div class="flex flex-col gap-2">
					<p class="text-base text-ink-gray-7">{{ __("Upload a font file of your own. Everyone in the workspace can use it.") }}</p>
					<div>
						<Button icon-left="lucide-upload" :label="__('Upload a Font')" :loading="sending" @click="picker.click()" />
						<input ref="picker" type="file" class="hidden" accept=".ttf,.otf,.woff,.woff2" @change="uploaded" />
					</div>
				</div>
				<hr class="border-t border-outline-gray-1" />
				<div v-if="library.google" class="flex flex-col gap-2">
					<p class="text-base text-ink-gray-7">{{ __("Or add a family from Google Fonts. It is kept in the workspace from then on.") }}</p>
					<TextInput v-model="query" :placeholder="__('Search Google Fonts')" @update:model-value="search" />
					<div class="flex max-h-72 flex-col overflow-y-auto">
						<div v-for="one in found" :key="one.family" class="flex items-center gap-3 border-b border-outline-gray-1 py-2">
							<span class="text-base text-ink-gray-8">{{ one.family }}</span>
							<span class="text-sm text-ink-gray-5">{{ one.arabic ? __("Arabic") : "" }}</span>
							<Button class="ms-auto" size="sm" :label="added.has(one.family) ? __('Added') : __('Add')" :disabled="added.has(one.family)" :loading="adding === one.family" @click="add(one.family)" />
						</div>
						<p v-if="query && !found.length && !looking" class="py-2 text-sm text-ink-gray-5">{{ __("No family by that name.") }}</p>
					</div>
				</div>
				<p v-else class="text-sm text-ink-gray-5">{{ __("To add fonts from Google's catalogue, turn on Fonts from Google in {0}.", [name("trust_center")]) }}</p>
			</div>
	</Dialog>
</template>

<script setup>
import { ref } from "vue";
import { Button, Dialog, TextInput } from "frappe-ui";
import { alert, call, csrf, name } from "../../kit/desk";
import { library, loadFonts, refreshFaces } from "./fonts.js";
import { __ } from "./words.js";

const open = defineModel({ type: Boolean, default: false });
const picker = ref(null);
const sending = ref(false);
const query = ref("");
const found = ref([]);
const looking = ref(false);
const adding = ref("");
const added = ref(new Set());
let timer = null;

function search() {
	clearTimeout(timer);
	timer = setTimeout(async () => {
		looking.value = true;
		try {
			found.value = await call("onedesk.one_deck.fonts.google_search", { q: query.value });
		} finally {
			looking.value = false;
		}
	}, 300);
}

async function add(family) {
	adding.value = family;
	try {
		library.value = await call("onedesk.one_deck.fonts.google_add", { family });
		added.value = new Set([...added.value, family]);
		refreshFaces(picker.value.ownerDocument);
		alert(__("{0} added to the workspace's fonts.", [family]));
	} finally {
		adding.value = "";
	}
}

async function uploaded(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file) return;
	sending.value = true;
	try {
		const form = new FormData();
		form.append("file", file);
		const answer = await fetch("/api/method/onedesk.one_deck.fonts.upload", { method: "POST", body: form, headers: { "X-Frappe-CSRF-Token": csrf() } });
		const said = await answer.json();
		if (!answer.ok) throw new Error(said?._server_messages || said?.exception || answer.statusText);
		library.value = said.message;
		refreshFaces(picker.value.ownerDocument);
		alert(__("{0} added to the workspace's fonts.", [file.name]));
	} catch {
		alert(__("Could not add the font."), "red");
	} finally {
		sending.value = false;
	}
}

loadFonts();
</script>
