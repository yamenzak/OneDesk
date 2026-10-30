<template>
  <div :class="wide ? 'flex flex-col gap-1' : 'grid grid-cols-5 items-center gap-2'">
    <label class="col-span-2 truncate text-sm text-ink-gray-5" :title="spec.label">{{ spec.label }}</label>
    <div class="col-span-3 flex min-w-0 items-center gap-1">
      <template v-if="spec.type === 'number'">
        <TextInput class="min-w-0 flex-1" size="sm" type="number" :model-value="modelValue" :step="spec.step" :min="spec.min" :max="spec.max" :disabled="disabled" @update:model-value="number" />
        <span v-if="spec.unit" class="w-5 shrink-0 text-xs text-ink-gray-5">{{ spec.unit }}</span>
      </template>

      <template v-else-if="spec.type === 'colour'">
        <input
          type="color"
          class="h-7 w-7 shrink-0 cursor-pointer rounded-2 border border-outline-gray-2 bg-surface-base p-0"
          :value="swatch"
          :disabled="disabled"
          :aria-label="spec.label"
          @input="picked($event.target.value)"
        />
        <TextInput class="min-w-0 flex-1" size="sm" :model-value="modelValue" :placeholder="__('None')" :disabled="disabled" @update:model-value="typed" />
        <Button v-if="modelValue" variant="ghost" size="sm" icon="lucide-x" :tooltip="__('None')" :aria-label="__('None')" :disabled="disabled" @click="emit('update:modelValue', '')" />
      </template>

      <div v-else-if="spec.type === 'choice' && spec.icons" class="flex flex-wrap gap-0.5">
        <Button
          v-for="(option, i) in spec.options"
          :key="option"
          size="sm"
          :variant="modelValue === option ? 'subtle' : 'ghost'"
          :icon="glyph(spec.icons[i])"
          :tooltip="spec.labels[i]"
          :aria-label="spec.labels[i]"
          :disabled="disabled"
          @click="emit('update:modelValue', option)"
        />
      </div>

      <FormControl v-else-if="spec.type === 'choice'" class="min-w-0 flex-1" size="sm" type="select" :options="options" :model-value="modelValue" :disabled="disabled" @update:model-value="chosen" />

      <Switch v-else-if="spec.type === 'check'" size="sm" :model-value="Boolean(modelValue)" :disabled="disabled" @update:model-value="(on) => emit('update:modelValue', on ? 1 : 0)" />

      <template v-else-if="spec.type === 'file'">
        <span class="min-w-0 flex-1 truncate text-sm text-ink-gray-7" :title="modelValue">{{ modelValue ? modelValue.split("/").pop() : __("None") }}</span>
        <Button size="sm" variant="subtle" icon="lucide-upload" :tooltip="__('Upload')" :aria-label="__('Upload')" :disabled="disabled" @click="emit('upload')" />
        <Button v-if="modelValue" size="sm" variant="ghost" icon="lucide-x" :tooltip="__('Remove')" :aria-label="__('Remove')" :disabled="disabled" @click="emit('update:modelValue', '')" />
      </template>

      <Textarea
        v-else-if="spec.type === 'css' || (spec.type === 'text' && spec.max > 200)"
        class="w-full"
        :class="spec.type === 'css' ? 'font-mono' : ''"
        size="sm"
        :rows="spec.type === 'css' ? 5 : 3"
        :model-value="modelValue"
        :placeholder="spec.type === 'css' ? 'text-shadow: 0 4px 24px black;' : ''"
        :disabled="disabled"
        @update:model-value="(v) => emit('update:modelValue', v)"
      />

      <TextInput v-else class="min-w-0 flex-1" size="sm" :model-value="modelValue" :disabled="disabled" @update:model-value="(v) => emit('update:modelValue', v)" />
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Button, FormControl, Switch, TextInput, Textarea } from "frappe-ui";

import { __ } from "../../kit";
import { glyph } from "./icons";

const props = defineProps({
  spec: { type: Object, required: true },
  modelValue: { type: [String, Number], default: "" },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue", "upload"]);

const wide = computed(() => props.spec.type === "css" || (props.spec.type === "text" && props.spec.max > 200));
const options = computed(() => props.spec.options.map((value, i) => ({ value, label: props.spec.labels?.[i] ?? String(value) })));
const HEX = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;

// The native picker knows #rrggbb only: a colour's see-through part, the
// last two digits of #rrggbbaa, is kept when a new colour is picked.
const swatch = computed(() => {
  const value = String(props.modelValue || "");
  if (value.length === 4) return "#" + [...value.slice(1)].map((c) => c + c).join("");
  return value.length >= 7 ? value.slice(0, 7) : "#".padEnd(7, "0");
});

function picked(value) {
  const was = String(props.modelValue || "");
  emit("update:modelValue", value + (was.length === 9 ? was.slice(7) : ""));
}

function typed(value) {
  const said = String(value || "").trim();
  if (!said || HEX.test(said)) emit("update:modelValue", said);
}

function number(value) {
  const n = parseFloat(value);
  if (Number.isNaN(n)) return;
  emit("update:modelValue", Math.min(Math.max(n, props.spec.min), props.spec.max));
}

function chosen(value) {
  const match = props.spec.options.find((one) => String(one) === String(value));
  emit("update:modelValue", match ?? value);
}
</script>
