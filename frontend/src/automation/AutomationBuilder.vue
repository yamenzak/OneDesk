<template>
  <Loading v-if="!catalogue" />
  <StarterGrid v-else-if="picking" :starters="catalogue.starters" @pick="start" />
  <div v-else class="flex flex-col gap-3">
    <TextInput v-model="state.title" :placeholder="__('Name this automation')" :aria-label="__('Name')" :disabled="readonly" />
    <p v-if="problems.length && !readonly" class="text-p-sm text-ink-red-4">{{ problems[0] }}</p>
    <div class="flex flex-col gap-3 md:flex-row">
      <div class="h-80 overflow-hidden rounded-3 border border-outline-gray-2 md:h-96 md:min-w-0 md:flex-1" dir="ltr">
        <AutomationCanvas
          :nodes="drawn.nodes"
          :edges="drawn.edges"
          :selected-id="selected"
          :block-options="blockOptions"
          :readonly="readonly"
          @select="selected = $event"
          @add-node="added"
        />
      </div>
      <StepPanel
        class="md:w-80 md:shrink-0"
        :step="step"
        :id="selected"
        :catalogue="catalogue"
        :block-options="blockOptions"
        :readonly="readonly"
        @remove="removed"
        @move="moved"
        @add="added({ afterId: selected, branch: null, value: $event })"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { TextInput, debounce } from "frappe-ui";
import { AutomationCanvas } from "@framework/ui/AutomationCanvas";

import { __, call, get, name, Loading } from "../kit";
import { lucide } from "./icons";
import { START, add, bare, lay, made, move, remove, shown, stepAt } from "./layout";
import StarterGrid from "./StarterGrid.vue";
import StepPanel from "./StepPanel.vue";

const C = "onedesk.one.automation_center.";

const props = defineProps({
  trigger: { type: String, required: true },
  scope: { type: String, required: true },
  automation: { type: String, default: null },
  readonly: { type: Boolean, default: false },
  onChange: { type: Function, default: null },
});

const catalogue = ref(null);
const picking = ref(false);
const state = reactive({ title: "", steps: [] });
const selected = ref(START);
const problems = ref([]);

const ai = () => name("one_ai");
const id = () => Math.random().toString(36).slice(2, 8);

const actionOf = (key) => (catalogue.value?.actions || []).find((one) => one.key === key);
const conditionOf = (key) => (catalogue.value?.conditions || []).find((one) => one.key === key);
const opOf = (key) => (catalogue.value?.ops || []).find((one) => one.value === key)?.label || key;

function conditionWords(one) {
  if ("items" in one) return one.items.map(conditionWords).join(one.any ? __(" or ") : " · ");
  const block = conditionOf(one.field);
  if (!block) return "";
  if (block.kind === "flag") return one.value === false ? block.no : block.label;
  if (block.kind === "kind") return `${block.label} ${one.op === "is_not" ? __("isn't a") : __("is a")} ${__(one.value || "")}`;
  return `${block.label} ${opOf(one.op || "contains")} ${one.value || "…"}`;
}

function paramWords(step, block) {
  return (block?.params || [])
    .filter((param) => shown(param, step) && param.type !== "long" && step[param.key] !== undefined && step[param.key] !== "")
    .map((param) => {
      const value = step[param.key];
      if (param.type === "choice") return param.options.find((one) => one.value === value)?.label || value;
      if (param.type === "switch") return value ? param.label : "";
      return value;
    })
    .filter(Boolean)
    .join(" · ");
}

function issue(step) {
  if (step.type === "if") {
    const blank = (step.test?.items || []).some(function empty(one) {
      return "items" in one ? one.items.some(empty) : conditionOf(one.field)?.kind === "text" && !String(one.value || "").trim();
    });
    return blank ? { level: "warning", message: __("Write what each condition looks for.") } : null;
  }
  if (step.type === "ask") {
    if (!catalogue.value.reads && catalogue.value.unread) return { level: "warning", message: catalogue.value.unread };
    if (step.ask !== "pick" && !(step.question || "").trim()) return { level: "warning", message: __("Write the question for {0}.", [ai()]) };
    return null;
  }
  const block = actionOf(step.type);
  if (step.type !== "stop" && !block) return { level: "error", message: __("That cannot be set.") };
  const missing = (block?.params || []).find((param) => param.needed && shown(param, step) && !String(step[param.key] ?? "").trim());
  return missing ? { level: "warning", message: __("Fill in {0}.", [missing.label]) } : null;
}

function describe(step) {
  const block = actionOf(step.type);
  const said = { issue: issue(step) || undefined };
  if (step.type === "if") return { ...said, kicker: __("Check"), label: __("If"), detail: conditionWords(step.test || { items: [] }) || __("any message"), icon: lucide("split"), tone: "green" };
  if (step.type === "ask") {
    const asked = step.ask === "pick" ? (step.labels || []).map((one) => one.label).join(", ") : step.question;
    return { ...said, kicker: ai(), label: __("Ask {0}", [ai()]), detail: asked || "", icon: lucide("oneai"), tone: "violet" };
  }
  if (step.type === "stop") return { ...said, kicker: __("Do"), label: __("Stop Here"), detail: __("Stop, and skip the rules after this one"), icon: lucide("octagon"), tone: "red" };
  return { ...said, kicker: block?.group || __("Do"), label: block?.label || step.type, detail: paramWords(step, block), icon: lucide(block?.icon), tone: block?.ai ? "violet" : "blue" };
}

const drawn = computed(() => {
  if (!catalogue.value) return { nodes: [], edges: [] };
  const trigger = catalogue.value.trigger;
  const start = { kicker: __("Trigger"), label: trigger.label, detail: trigger.where, icon: lucide(trigger.icon), tone: "blue" };
  return lay(state.steps, start, describe, __);
});

const blockOptions = computed(() => {
  if (!catalogue.value) return [];
  const checks = [{ value: "if", label: __("If"), icon: lucide("split"), tone: "green" }];
  if (catalogue.value.ai && catalogue.value.trigger.reads) checks.push({ value: "ask", label: __("Ask {0}", [ai()]), icon: lucide("oneai"), tone: "violet" });
  const groups = [{ group: __("Check"), options: checks }];
  for (const one of catalogue.value.actions) {
    let held = groups.find((group) => group.group === (one.group || __("Do")));
    if (!held) groups.push((held = { group: one.group || __("Do"), options: [] }));
    held.options.push({ value: one.key, label: one.label, icon: lucide(one.icon), tone: one.ai ? "violet" : "blue" });
  }
  groups.push({ group: __("Do"), options: [{ value: "stop", label: __("Stop Here"), icon: lucide("octagon"), tone: "red" }] });
  return groups;
});

const step = computed(() => stepAt(state.steps, selected.value));

function added({ afterId, branch, value }) {
  selected.value = add(state.steps, afterId, branch, made(value, catalogue.value, id()));
}

function removed() {
  remove(state.steps, selected.value);
  selected.value = START;
}

function moved(by) {
  selected.value = move(state.steps, selected.value, by);
}

function start(starter) {
  state.title = starter.rule.title || "";
  state.steps = bare(starter.rule.steps);
  picking.value = false;
}

const checked = debounce(async () => {
  problems.value = await call(C + "problems", { trigger: props.trigger, steps: JSON.stringify(state.steps) });
}, 400);

watch(
  state,
  () => {
    props.onChange?.({ title: state.title, steps: bare(state.steps) });
    if (!props.readonly) checked();
  },
  { deep: true }
);

onMounted(async () => {
  catalogue.value = await get(C + "blocks", { trigger: props.trigger, scope: props.scope });
  if (props.automation) {
    const held = await get(C + "automation", { name: props.automation });
    state.title = held.title || "";
    state.steps = held.steps || [];
  } else picking.value = true;
});
</script>
