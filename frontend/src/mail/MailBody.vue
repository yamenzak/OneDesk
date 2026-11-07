<template>
  <div>
    <div v-if="held" class="mb-2 flex items-center gap-2 rounded-3 bg-surface-gray-1 px-3 py-2 text-sm text-ink-gray-6">
      <span class="lucide-image-off size-4" aria-hidden="true" />
      <span class="flex-1">{{ __("Remote pictures are hidden.") }}</span>
      <Button size="sm" variant="subtle" :label="__('Show pictures')" @click="allowed = true" />
    </div>
    <iframe
      ref="frame"
      class="block w-full rounded-3 border-0"
      sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin"
      referrerpolicy="no-referrer"
      :title="__('Message')"
      :srcdoc="page"
      @load="fit"
    />
  </div>
</template>

<script setup>
// A message's own HTML in a sandboxed frame (mail.js, framePage).
import { computed, onBeforeUnmount, ref } from "vue";
import { Button } from "frappe-ui";

import { __ } from "../kit";
import { framePage } from "./mail";

const props = defineProps({ content: { type: String, default: "" } });

const frame = ref(null);
const allowed = ref(false);

const dark = ref(false);
const seen = () => (dark.value = document.documentElement.dataset.theme === "dark");
seen();
const theme = new MutationObserver(seen);
theme.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
onBeforeUnmount(() => theme.disconnect());

const framed = computed(() => framePage(props.content, allowed.value, dark.value));
const page = computed(() => framed.value.page);
const held = computed(() => framed.value.held);

// The frame is as tall as the message, so the conversation scrolls as one.
function fit() {
  const el = frame.value;
  const inner = el?.contentDocument?.documentElement;
  if (!inner) return;
  const size = () => {
    el.style.height = "1px";
    el.style.height = `${inner.scrollHeight + 2}px`;
  };
  size();
  el.contentDocument.querySelectorAll("img").forEach((img) => img.addEventListener("load", size));
}
</script>
