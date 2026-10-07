<template>
  <!-- A record's views as one row of frappe-ui's tabs, as a form's tabs run
       across the top (docs/PASSOVER.md, A record's page). Those that do not
       fit are under More at the end of the row, which reads as the chosen
       view while that is one of them. The row scrolls with the page. -->
  <div ref="row" class="relative flex min-w-0 items-center border-b border-outline-gray-2">
    <!-- Every tab, out of sight, to measure where each ends. -->
    <div ref="ruler" inert aria-hidden="true" class="pointer-events-none invisible absolute start-0 top-0 flex whitespace-nowrap">
      <Tabs :model-value="modelValue">
        <TabList class="border-0">
          <TabTrigger v-for="one in views" :key="one.key" :value="one.key" :label="one.label" :icon-left="one.icon">
            <template v-if="one.count" #suffix><span class="ms-1 text-sm text-ink-gray-5">{{ one.count }}</span></template>
          </TabTrigger>
        </TabList>
      </Tabs>
    </div>
    <Tabs :model-value="chosenShown ? modelValue : null" class="min-w-0" @update:model-value="pick">
      <TabList class="border-0">
        <TabTrigger v-for="one in shown" :key="one.key" :value="one.key" :label="one.label" :icon-left="one.icon">
          <template v-if="one.count" #suffix><span class="ms-1 text-sm text-ink-gray-5">{{ one.count }}</span></template>
        </TabTrigger>
      </TabList>
    </Tabs>
    <Dropdown v-if="hidden.length" :options="more" align="end">
      <template #trigger>
        <Button
          ref="moreButton"
          size="sm"
          :variant="chosenShown ? 'ghost' : 'subtle'"
          :icon-left="chosenShown ? null : chosen?.icon"
          icon-right="lucide-chevron-down"
          :label="chosenShown ? __('More') : chosen?.label"
          class="ms-1 shrink-0"
        />
      </template>
    </Dropdown>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Button, Dropdown, TabList, Tabs, TabTrigger } from "frappe-ui";

import { __ } from "./desk";

const props = defineProps({
  modelValue: { type: String, default: null },
  // `{ key, label, icon?, count? }`, in their order.
  views: { type: Array, required: true },
});
const emit = defineEmits(["update:modelValue"]);

// Room kept at the end of the row for More, wide enough for a view's name.
const MORE = 140;
const row = ref(null);
const ruler = ref(null);
const fit = ref(props.views.length);

const shown = computed(() => props.views.slice(0, fit.value));
const hidden = computed(() => props.views.slice(fit.value));
const chosen = computed(() => props.views.find((one) => one.key === props.modelValue));
const chosenShown = computed(() => shown.value.some((one) => one.key === props.modelValue));
const more = computed(() =>
  hidden.value.map((one) => ({
    label: one.count ? `${one.label} (${one.count})` : one.label,
    icon: one.icon,
    onClick: () => pick(one.key),
  }))
);

function pick(key) {
  if (key && key !== props.modelValue) emit("update:modelValue", key);
}

// How many tabs fit: all of them, or as many as leave room for More.
function measure() {
  if (!row.value || !ruler.value) return;
  const room = row.value.clientWidth;
  const start = ruler.value.getBoundingClientRect().left;
  const ends = [...ruler.value.querySelectorAll("[role=tab]")].map((tab) => tab.getBoundingClientRect().right - start);
  if (!ends.length || ends[ends.length - 1] <= room) {
    fit.value = props.views.length;
    return;
  }
  fit.value = Math.max(1, ends.filter((end) => end <= room - MORE).length);
}

let watcher = null;
onMounted(() => {
  watcher = new ResizeObserver(() => measure());
  watcher.observe(row.value);
  measure();
});
onBeforeUnmount(() => watcher?.disconnect());
watch(
  () => props.views.map((one) => `${one.key}:${one.label}:${one.count ?? ""}`).join("|"),
  () => nextTick(measure)
);
</script>
