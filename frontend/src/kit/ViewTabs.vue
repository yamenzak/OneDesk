<template>
  <div class="relative min-w-0 border-b border-outline-gray-2">
    <div ref="row" class="overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" @scroll="edges">
      <Tabs :model-value="modelValue" class="w-max" @update:model-value="pick">
        <TabList class="flex-nowrap whitespace-nowrap border-0">
          <TabTrigger v-for="one in views" :key="one.key" :value="one.key" :label="one.label" :icon-left="one.icon">
            <template v-if="one.count" #suffix><span class="ms-1 text-sm text-ink-gray-5">{{ one.count }}</span></template>
          </TabTrigger>
        </TabList>
      </Tabs>
    </div>
    <div v-if="before" aria-hidden="true" class="pointer-events-none absolute inset-y-0 start-0 w-10 bg-gradient-to-r from-surface-base to-transparent rtl:bg-gradient-to-l" />
    <div v-if="after" aria-hidden="true" class="pointer-events-none absolute inset-y-0 end-0 w-10 bg-gradient-to-l from-surface-base to-transparent rtl:bg-gradient-to-r" />
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { TabList, Tabs, TabTrigger } from "frappe-ui";

const props = defineProps({
  modelValue: { type: String, default: null },
  views: { type: Array, required: true },
});
const emit = defineEmits(["update:modelValue"]);

const row = ref(null);
const before = ref(false);
const after = ref(false);

function pick(key) {
  if (key && key !== props.modelValue) emit("update:modelValue", key);
}

function edges() {
  const el = row.value;
  if (!el) return;
  const gone = Math.abs(el.scrollLeft);
  before.value = gone > 1;
  after.value = gone + el.clientWidth < el.scrollWidth - 1;
}

function reveal() {
  const el = row.value;
  const tab = el?.querySelector("[role=tab][aria-selected=true]");
  if (!tab) return edges();
  const box = el.getBoundingClientRect();
  const at = tab.getBoundingClientRect();
  if (at.left < box.left) el.scrollLeft -= box.left - at.left + 24;
  else if (at.right > box.right) el.scrollLeft += at.right - box.right + 24;
  edges();
}

let watcher = null;
onMounted(() => {
  watcher = new ResizeObserver(() => edges());
  watcher.observe(row.value);
  nextTick(reveal);
});
onBeforeUnmount(() => watcher?.disconnect());
watch(() => props.modelValue, () => nextTick(reveal));
watch(
  () => props.views.map((one) => `${one.key}:${one.label}:${one.count ?? ""}`).join("|"),
  () => nextTick(reveal)
);
</script>
