<!-- A presentation in the desk: Suite's slides editor, opened on the presentation the route names, under a head that leads back to where it belongs (shim/EditorNavbar.vue). -->
<template>
	<div ref="pageEl" data-tour="onedeck-editor" class="one-presentation relative h-full w-full overflow-hidden bg-surface-base">
		<div ref="shelfEl" class="pointer-events-none invisible fixed left-0 top-0 h-0 w-screen" aria-hidden="true" />
		<div v-if="failed" class="flex h-full items-center justify-center text-base text-ink-gray-6">{{ failed }}</div>
		<router-view v-else-if="rooted" v-slot="{ Component }">
			<keep-alive :max="2">
				<component :is="Component" />
			</keep-alive>
		</router-view>
	</div>
</template>

<script setup>
// Suite's stores import each other in a ring (element → text editor → helpers →
// media uploads → presentation → slide → element). Element has to be the one
// entered first, as it is in Suite, or it calls the text editor before the
// helpers it uses exist; so it is loaded here, before anything else.
import "./stores/element";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { __, aiSees, alert, call, editorOn, name as appName } from "../kit/desk";
import { allow, holdRouter } from "./shim/router.js";
import { audience } from "./shim/presenter.js";
import { setSlideRoot } from "./shim/root.js";
import { pageFonts } from "./shim/fonts.js";

const props = defineProps({ route: { type: Array, default: () => [] }, query: { type: Object, default: () => ({}) } });

const router = useRouter();
holdRouter(router);
const pageEl = ref(null);
const shelfEl = ref(null);
const rooted = ref(false);
const failed = ref("");

// The workspace's fonts are faces a slide may be written in (shim/fonts.js);
// a face is the page's, not the island's, so it is declared once in the page.
function fonts() {
	pageFonts(document);
}

async function open(name) {
	if (!name) return;
	failed.value = "";
	const said = await call("onedesk.one_deck.api.get_editor_access", { presentation_id: name });
	if (said === "none") {
		failed.value = __("You do not have permission to open this presentation.");
		return;
	}
	allow(said);
	if (said === "view" && !editorOn("presentation")) alert(__("{0} is turned off for this workspace, so this opens read-only.", [appName("one_deck")]), "blue");
	// the audience's window, opened from the presenter view, plays the slides and nothing else
	audience.value = Boolean(props.query.audience);
	const page = audience.value ? "slides-slideshow" : "slides-editor";
	await router.replace({ name: page, params: { presentationId: name }, query: { slide: props.query.slide || 1 } });
}

onMounted(() => {
	fonts();
	setSlideRoot(pageEl.value.getRootNode(), shelfEl.value);
	rooted.value = true;
});
watch(() => props.route[0], open, { immediate: true });

onBeforeUnmount(() => {
	aiSees(null);
	router.replace({ name: "slides-blank" });
});
</script>
