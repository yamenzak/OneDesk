<template>
  <div class="flex flex-wrap items-center gap-2">
    <Select class="min-w-36 flex-1" :model-value="picked" :options="fields" :aria-label="__('Condition')" :disabled="readonly" @update:model-value="pick" />
    <template v-if="block && block.kind === 'text'">
      <Select class="min-w-28" :model-value="condition.op || 'contains'" :options="catalogue.ops" :aria-label="__('Test')" :disabled="readonly" @update:model-value="set({ op: $event })" />
      <TextInput class="min-w-36 flex-1" :model-value="condition.value || ''" :placeholder="__('words, with commas')" :aria-label="__('Value')" :disabled="readonly" @update:model-value="set({ value: $event })" />
    </template>
    <template v-else-if="block && block.kind === 'kind'">
      <Select class="min-w-24" :model-value="condition.op || 'is'" :options="kindOps" :aria-label="__('Test')" :disabled="readonly" @update:model-value="set({ op: $event })" />
      <Select class="min-w-28 flex-1" :model-value="condition.value" :options="block.options" :aria-label="__('Value')" :disabled="readonly" @update:model-value="set({ value: $event })" />
    </template>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Select, TextInput } from "frappe-ui";

import { __ } from "../kit";

const props = defineProps({
  condition: { type: Object, required: true },
  catalogue: { type: Object, required: true },
  readonly: { type: Boolean, default: false },
});
const emit = defineEmits(["update"]);

const kindOps = [
  { value: "is", label: __("is a") },
  { value: "is_not", label: __("isn't a") },
];

const block = computed(() => (props.catalogue.conditions || []).find((one) => one.key === props.condition.field));

const fields = computed(() =>
  (props.catalogue.conditions || []).flatMap((one) =>
    one.kind === "flag"
      ? [
          { value: `${one.key}:1`, label: one.label },
          { value: `${one.key}:0`, label: one.no },
        ]
      : [{ value: one.key, label: one.label }]
  )
);

const picked = computed(() => (block.value?.kind === "flag" ? `${props.condition.field}:${props.condition.value === false ? 0 : 1}` : props.condition.field));

function set(change) {
  emit("update", { ...props.condition, ...change });
}

function pick(value) {
  const [field, flag] = String(value).split(":");
  const chosen = (props.catalogue.conditions || []).find((one) => one.key === field);
  if (!chosen) return;
  if (chosen.kind === "flag") emit("update", { field, value: flag === "1" });
  else if (chosen.kind === "kind") emit("update", { field, op: "is", value: chosen.options[0]?.value });
  else emit("update", { field, op: "contains", value: "" });
}
</script>
