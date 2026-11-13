<template>
  <div class="flex flex-col gap-4">
    <template v-for="one in step.fields" :key="one.fieldname">
      <Switch v-if="one.fieldtype === 'Check'" v-model="values[one.fieldname]" padded :label="one.label" :description="one.description" />
      <FormControl
        v-else
        v-model="values[one.fieldname]"
        size="lg"
        :type="TYPES[one.fieldtype] || 'text'"
        :label="one.label"
        :description="one.description"
        :options="one.options.map((option) => ({ label: option, value: option }))"
      />
    </template>
  </div>
</template>

<script setup>
import { computed, reactive } from "vue";
import { FormControl, Switch } from "frappe-ui";

import { answers } from "./wizard";

const props = defineProps({ step: { type: Object, required: true } });

const TYPES = { Select: "select", Int: "number", Float: "number", "Small Text": "textarea", Text: "textarea", Date: "date" };

const kept = answers.steps?.[props.step.app]?.[props.step.key] || {};
const values = reactive(
  Object.fromEntries(props.step.fields.map((one) => [one.fieldname, kept[one.fieldname] ?? (one.fieldtype === "Check" ? Boolean(Number(one.default ?? 0)) : (one.default ?? ""))])),
);

const given = () => Object.fromEntries(props.step.fields.map((one) => [one.fieldname, one.fieldtype === "Check" ? Number(values[one.fieldname]) : values[one.fieldname]]));

defineExpose({
  ready: computed(() => true),
  said: () => ({ answers: { steps: { [props.step.app]: { [props.step.key]: given() } } } }),
});
</script>
