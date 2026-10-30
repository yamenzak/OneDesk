<!-- A presentation in the desk: Suite's slides editor, opened on the presentation the route names, under a head that leads back to where it belongs (shim/EditorNavbar.vue). -->
<template>
	<div ref="pageEl" class="one-presentation relative h-full w-full overflow-hidden bg-surface-base">
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

import { __, aiSees, call } from "../kit/desk";
import { allow, holdRouter } from "./shim/router.js";
import { setSlideRoot } from "./shim/root.js";

const props = defineProps({ route: { type: Array, default: () => [] }, query: { type: Object, default: () => ({}) } });

const FONTS = "/assets/onedesk/slide/fonts.css";
const router = useRouter();
holdRouter(router);
const pageEl = ref(null);
const shelfEl = ref(null);
const rooted = ref(false);
const failed = ref("");

// Anton and Courier Prime are faces a slide may be written in; a face is the
// page's, not the island's, so it is declared once in the page.
function fonts() {
	if (document.head.querySelector(`link[href="${FONTS}"]`)) return;
	const link = document.createElement("link");
	link.rel = "stylesheet";
	link.href = FONTS;
	document.head.appendChild(link);
}

async function open(name) {
	if (!name) return;
	failed.value = "";
	const said = await call("onedesk.one_slide.api.get_editor_access", { presentation_id: name });
	if (said === "none") {
		failed.value = __("You do not have permission to open this presentation.");
		return;
	}
	allow(said);
	await router.replace({ name: "slides-editor", params: { presentationId: name }, query: { slide: props.query.slide || 1 } });
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
