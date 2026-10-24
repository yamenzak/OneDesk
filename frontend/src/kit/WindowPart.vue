<template>
  <span ref="anchor" hidden />
  <Teleport v-if="target" :to="target"><slot /></Teleport>
</template>

<script setup>
// A part of an island drawn where the window keeps it (the nav pane, the
// details pane, the command row), and still part of the same island: one
// Vue app and one state. The window's parts are desk's, outside the island's
// shadow root, so the part gets a shadow root of its own there, given the
// island's own stylesheets and theme.
import { onBeforeUnmount, onMounted, ref } from "vue";

import { windowPart } from "./desk";

const props = defineProps({
  win: { type: Object, default: null },
  part: { type: String, required: true },
  detailsKey: { type: String, default: "page" },
  width: { type: Number, default: undefined },
  inline: Boolean,
});

const anchor = ref(null);
const target = ref(null);
let host = null;
let watching = null;

onMounted(() => {
  const at = windowPart(props.win, props.part, { key: props.detailsKey, width: props.width });
  if (!at) return;
  const mine = anchor.value.getRootNode();
  host = document.createElement(props.inline ? "span" : "div");
  host.className = `one-island-part one-island-part-${props.part}`;
  at.append(host);
  const shadow = host.attachShadow({ mode: "open" });
  shadow.adoptedStyleSheets = [...(mine.adoptedStyleSheets || [])];
  const root = document.createElement(props.inline ? "span" : "div");
  const theirs = mine.querySelector?.(".frappe-island-root");
  root.setAttribute("data-theme", theirs?.getAttribute("data-theme") || "light");
  if (theirs) {
    watching = new MutationObserver(() => root.setAttribute("data-theme", theirs.getAttribute("data-theme") || "light"));
    watching.observe(theirs, { attributes: true, attributeFilter: ["data-theme"] });
  }
  shadow.append(root);
  target.value = root;
});

onBeforeUnmount(() => {
  watching?.disconnect();
  host?.remove();
});
</script>
