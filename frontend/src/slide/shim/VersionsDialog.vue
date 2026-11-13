<!-- A presentation's history: every version kept, newest first, each one a way back; and the slides as they are now kept under a name. -->
<template>
	<Dialog v-model:open="open" :title="__('Version History')" size="lg">
			<div class="flex flex-col gap-4">
				<div v-if="writable" class="flex items-end gap-2">
					<TextInput v-model="title" class="flex-1" :placeholder="__('Name this version')" @keydown.enter="keep" />
					<Button :label="__('Keep')" :loading="keeping" :disabled="!title.trim()" @click="keep" />
				</div>
				<p v-if="!versions.length" class="text-base text-ink-gray-5">{{ __("No versions yet. One is kept as you work, at most every ten minutes.") }}</p>
				<div v-else class="flex max-h-96 flex-col divide-y divide-outline-gray-1 overflow-y-auto">
					<div v-for="one in versions" :key="one.name" class="flex items-center gap-3 py-2">
						<div class="min-w-0 flex-1">
							<div class="truncate text-base text-ink-gray-8">{{ one.title || when(one.at) }}</div>
							<div class="truncate text-sm text-ink-gray-5">{{ __("{0} · {1} slides", [one.by, one.slides]) }}<span v-if="one.title"> · {{ when(one.at) }}</span></div>
						</div>
						<Button v-if="writable" variant="subtle" :label="__('Go Back to This')" :loading="restoring === one.name" @click="restore(one)" />
					</div>
				</div>
			</div>
	</Dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { Button, Dialog, TextInput } from "frappe-ui";

import { __, ago, call, date } from "../../kit/desk";

const props = defineProps({ name: { type: String, default: "" }, writable: { type: Boolean, default: false } });
const emit = defineEmits(["restored"]);
const open = defineModel({ type: Boolean, default: false });
const versions = ref([]);
const title = ref("");
const keeping = ref(false);
const restoring = ref(null);

const when = (at) => `${date(at)} · ${ago(at)}`;

async function load() {
	versions.value = await call("onedesk.one_deck.versions.listed", { name: props.name });
}
watch(open, (now) => now && load());

async function keep() {
	if (!title.value.trim()) return;
	keeping.value = true;
	try {
		await call("onedesk.one_deck.versions.keep", { name: props.name, title: title.value.trim() });
		title.value = "";
		await load();
	} finally {
		keeping.value = false;
	}
}

async function restore(one) {
	restoring.value = one.name;
	try {
		emit("restored", await call("onedesk.one_deck.versions.restore", { name: props.name, version: one.name }));
		open.value = false;
	} finally {
		restoring.value = null;
	}
}
</script>
