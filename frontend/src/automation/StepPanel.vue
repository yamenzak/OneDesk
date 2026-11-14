<template>
  <aside class="flex flex-col gap-3 rounded-3 border border-outline-gray-2 bg-surface-base p-3">
    <div class="flex items-start gap-2">
      <div class="min-w-0 flex-1">
        <div class="text-sm text-ink-gray-5">{{ head.kicker }}</div>
        <div class="truncate text-base font-semibold text-ink-gray-9">{{ head.label }}</div>
      </div>
      <template v-if="step && !readonly">
        <Button variant="ghost" icon="lucide-arrow-up" :aria-label="__('Move Up')" :title="__('Move Up')" @click="emit('move', -1)" />
        <Button variant="ghost" icon="lucide-arrow-down" :aria-label="__('Move Down')" :title="__('Move Down')" @click="emit('move', 1)" />
        <Button variant="ghost" icon="lucide-trash-2" :aria-label="__('Remove Step')" :title="__('Remove Step')" @click="emit('remove')" />
      </template>
    </div>

    <p v-if="!step" class="text-p-sm text-ink-gray-6">{{ __("Pick a step to change it, or add one after it with the plus.") }}</p>

    <ConditionBuilder
      v-else-if="step.type === 'if'"
      :model-value="conditions"
      :new-condition="fresh"
      :max-depth="2"
      bordered="root"
      :readonly="readonly"
      @update:model-value="setConditions"
    >
      <template #condition="{ condition, update }">
        <ConditionRow :condition="condition" :catalogue="catalogue" :readonly="readonly" @update="update" />
      </template>
    </ConditionBuilder>

    <template v-else-if="step.type === 'ask'">
      <FormControl v-model="step.ask" type="select" :label="__('Ask')" :options="askings" :disabled="readonly" />
      <FormControl v-if="step.ask !== 'pick'" v-model="step.question" type="textarea" :label="__('Question')" :placeholder="__('a complaint')" :disabled="readonly" />
      <template v-else>
        <div v-for="(one, n) in step.labels" :key="n" class="flex flex-col gap-2 rounded-3 bg-surface-gray-1 p-2">
          <div class="flex items-end gap-2">
            <FormControl v-model="one.label" class="flex-1" type="text" :label="__('Label')" :placeholder="__('Such as Quote Request.')" :disabled="readonly" />
            <Button v-if="!readonly" variant="ghost" icon="lucide-x" :aria-label="__('Remove')" @click="step.labels.splice(n, 1)" />
          </div>
          <FormControl v-model="one.about" type="text" :label="__('Meaning')" :description="__('Optional, and helps {0} tell it apart.', [ai])" :disabled="readonly" />
        </div>
        <Button v-if="!readonly" icon-left="lucide-plus" :label="__('Label')" @click="(step.labels = step.labels || []).push({ label: '', about: '', then: [] })" />
      </template>
      <p v-if="!catalogue.reads && catalogue.unread" class="text-p-sm text-ink-amber-4">{{ catalogue.unread }}</p>
    </template>

    <p v-else-if="step.type === 'stop'" class="text-p-sm text-ink-gray-6">{{ __("Stop, and skip the rules after this one") }}</p>

    <template v-else-if="block">
      <template v-for="param in block.params" :key="param.key">
        <template v-if="shown(param, step)">
          <Switch
            v-if="param.type === 'switch'"
            :model-value="!!step[param.key]"
            :label="param.label"
            :description="param.description"
            :disabled="readonly"
            @update:model-value="step[param.key] = $event ? 1 : 0"
          />
          <FormControl
            v-else
            v-model="step[param.key]"
            :type="controls[param.type] || 'text'"
            :label="param.label"
            :description="param.description"
            :placeholder="param.placeholder"
            :options="param.type === 'choice' ? param.options : undefined"
            :disabled="readonly"
          />
        </template>
      </template>
      <p v-if="!block.params.length" class="text-p-sm text-ink-gray-6">{{ __("Nothing to set.") }}</p>
    </template>

    <Dropdown v-if="!readonly && !(step && step.type === 'stop')" :options="adding">
      <Button icon-left="lucide-plus" :label="step ? __('Add Step After') : __('Add Step')" />
    </Dropdown>
  </aside>
</template>

<script setup>
import { computed } from "vue";
import { Button, Dropdown, FormControl, Switch } from "frappe-ui";
import { ConditionBuilder } from "@framework/ui/ConditionBuilder";

import { __, name } from "../kit";
import ConditionRow from "./ConditionRow.vue";
import { group, shown, tree } from "./layout";

const props = defineProps({
  step: { type: Object, default: null },
  id: { type: String, default: "" },
  catalogue: { type: Object, required: true },
  blockOptions: { type: Array, default: () => [] },
  readonly: { type: Boolean, default: false },
});
const emit = defineEmits(["remove", "move", "add"]);

const ai = name("one_ai");
const controls = { text: "text", email: "email", long: "textarea", choice: "select" };
const askings = [
  { value: "yes", label: __("A Question") },
  { value: "pick", label: __("Labels to Pick From") },
];

const block = computed(() => (props.catalogue.actions || []).find((one) => one.key === props.step?.type));

const head = computed(() => {
  const step = props.step;
  if (!step) return { kicker: __("Trigger"), label: `${props.catalogue.trigger.label} · ${props.catalogue.trigger.where}` };
  if (step.type === "if") return { kicker: __("Check"), label: __("If") };
  if (step.type === "ask") return { kicker: ai, label: __("Ask {0}", [ai]) };
  if (step.type === "stop") return { kicker: __("Do"), label: __("Stop Here") };
  return { kicker: block.value?.group || __("Do"), label: block.value?.label || step.type };
});

const conditions = computed(() => tree(props.step?.test));

function setConditions(value) {
  props.step.test = group(value);
}

function fresh() {
  const first = (props.catalogue.conditions || []).find((one) => one.kind === "text") || props.catalogue.conditions[0];
  return { field: first.key, op: "contains", value: "" };
}

const adding = computed(() =>
  props.blockOptions.map((one) => ({
    group: one.group,
    options: one.options.map((option) => ({ label: option.label, icon: option.icon, onClick: () => emit("add", option.value) })),
  }))
);
</script>
