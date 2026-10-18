<template>
  <Drawer :open="Boolean(task)" :title="task?.subject" @close="$emit('close')">
    <template #head>
      <Pill v-if="task" :value="task.status" :options="work.statuses" :colors="TASK_STATUS" :label="__('Status')" :readonly="!canWrite" @change="(v) => $emit('set', task.name, 'status', v)" />
    </template>
    <template #actions>
      <Button v-if="task && canTime" variant="ghost" :icon="timing ? 'lucide-square' : 'lucide-play'" :aria-label="timing ? __('Stop Timer') : __('Start Timer')" @click="time" />
      <Dropdown v-if="task" :options="menu">
        <Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Menu')" />
      </Dropdown>
    </template>
    <div v-if="task" class="flex flex-col gap-6 px-5 py-5">
      <input
        :value="task.subject"
        class="w-full rounded-3 border-0 bg-transparent px-0 text-xl font-semibold text-ink-gray-9 focus:ring-0"
        :readonly="!canWrite"
        :aria-label="__('Subject')"
        @change="(e) => e.target.value.trim() && $emit('set', task.name, 'subject', e.target.value.trim())"
      />
      <dl class="grid grid-cols-[7rem_minmax(0,1fr)] items-center gap-y-3 text-base">
        <dt class="text-ink-gray-5">{{ __("Assigned To") }}</dt>
        <dd class="min-w-0"><People named :users="task.assigned" :people="work.people" :options="canWrite ? team : null" :groups="canWrite ? work.user_groups || [] : []" @add="(u) => $emit('give', task.name, u)" @group="(users) => $emit('give', task.name, users)" @remove="(u) => $emit('take', task.name, u)" /></dd>
        <dt class="text-ink-gray-5">{{ __("Priority") }}</dt>
        <dd><Pill :value="task.priority" :options="work.priorities" :colors="PRIORITY" :label="__('Priority')" :readonly="!canWrite" @change="(v) => $emit('set', task.name, 'priority', v)" /></dd>
        <dt class="text-ink-gray-5">{{ __("Expected Start Date") }}</dt>
        <dd class="w-44"><Due :value="task.exp_start_date" done :readonly="!canWrite" @change="(v) => $emit('set', task.name, 'exp_start_date', v)" /></dd>
        <dt class="text-ink-gray-5">{{ __("Expected End Date") }}</dt>
        <dd class="w-44"><Due :value="task.exp_end_date" :done="task.status === 'Completed'" :readonly="!canWrite" @change="(v) => $emit('set', task.name, 'exp_end_date', v)" /></dd>
        <dt class="text-ink-gray-5">{{ __("Expected Time") }}</dt>
        <dd class="flex items-center gap-1">
          <TextInput type="number" size="sm" variant="ghost" min="0" step="0.5" class="w-28 tabular-nums" :model-value="task.expected_time || ''" :disabled="!canWrite" :aria-label="__('Expected Time')" :placeholder="__('Set Hours')" @change="(e) => $emit('set', task.name, 'expected_time', Number(e.target.value) || 0)" />
          <span v-if="task.expected_time" class="text-ink-gray-5">{{ __("h") }}</span>
        </dd>
        <template v-if="task.actual_time">
          <dt class="text-ink-gray-5">{{ __("Actual Time") }}</dt>
          <dd class="text-ink-gray-8 tabular-nums">{{ hours(task.actual_time) }}</dd>
        </template>
        <dt class="text-ink-gray-5">{{ __("Milestone") }}</dt>
        <dd><Switch :model-value="Boolean(task.is_milestone)" :disabled="!canWrite" :aria-label="__('Milestone')" @update:model-value="(v) => $emit('set', task.name, 'is_milestone', v ? 1 : 0)" /></dd>
        <template v-if="task.is_milestone && task.one_bill_share">
          <dt class="text-ink-gray-5">{{ __("Bill on Completion") }}</dt>
          <dd class="text-ink-gray-8">{{ __("{0}% of the contract", [task.one_bill_share]) }}</dd>
        </template>
        <dt class="text-ink-gray-5">{{ __("Project") }}</dt>
        <dd class="truncate"><button :class="LINK" @click="go(`/desk/project/${encodeURIComponent(task.project)}`)">{{ work.groups.find((g) => g.key === task.project)?.title }}</button></dd>
        <template v-if="doc?.type">
          <dt class="text-ink-gray-5">{{ __("Type") }}</dt>
          <dd class="truncate text-ink-gray-8">{{ doc.type }}</dd>
        </template>
        <template v-if="task.parent_task">
          <dt class="text-ink-gray-5">{{ __("Parent Task") }}</dt>
          <dd class="truncate"><button :class="LINK" @click="$emit('open', task.parent_task)">{{ subject(task.parent_task) }}</button></dd>
        </template>
        <template v-if="waits.length">
          <dt class="self-start text-ink-gray-5">{{ __("Depends On") }}</dt>
          <dd class="flex min-w-0 flex-col gap-1">
            <button v-for="one in waits" :key="one.name" class="flex min-w-0 items-center gap-2 text-start hover:underline" @click="$emit('open', one.name)">
              <span class="lucide-circle-check size-4 shrink-0" :class="one.done ? 'text-ink-green-3' : 'text-ink-gray-4'" />
              <span class="truncate" :class="one.done ? 'text-ink-gray-5' : 'text-ink-gray-8'">{{ one.subject }}</span>
            </button>
          </dd>
        </template>
        <template v-if="doc?.auto_repeat">
          <dt class="text-ink-gray-5">{{ __("Repeats") }}</dt>
          <dd class="truncate"><button :class="LINK" @click="go(`/desk/auto-repeat/${doc.auto_repeat}`)">{{ repeat?.disabled ? __("Stopped") : __(repeat?.frequency || "Repeats") }}</button></dd>
        </template>
      </dl>

      <section>
        <div class="mb-2 flex items-center justify-between">
          <h3 class="text-base font-semibold text-ink-gray-9">{{ __("Description") }}</h3>
          <Button v-if="canWrite" variant="ghost" size="sm" icon="lucide-pencil" :aria-label="__('Edit Details')" @click="details" />
        </div>
        <div v-if="doc?.description" class="text-base leading-relaxed text-ink-gray-7 [&_p]:mb-2" v-html="doc.description" />
        <button v-else-if="canWrite" class="text-base text-ink-gray-5 hover:text-ink-gray-8" @click="details">{{ __("Add Description") }}</button>
      </section>

      <section v-if="steps.length || canWrite">
        <div class="mb-2 flex items-center justify-between">
          <h3 class="text-base font-semibold text-ink-gray-9">{{ __("Checklist") }}</h3>
          <span v-if="steps.length" class="text-sm tabular-nums text-ink-gray-5">{{ __("{0} of {1}", [steps.filter((one) => one.done).length, steps.length]) }}</span>
        </div>
        <div class="flex flex-col gap-1.5">
          <Checkbox v-for="one in steps" :key="one.name" :model-value="Boolean(one.done)" :label="one.step" :disabled="!canWrite" @update:model-value="(v) => tick(one, v)" />
        </div>
        <TextInput v-if="canWrite" v-model="newStep" size="sm" class="mt-2" :placeholder="__('Add Step')" @keydown.enter="addStep" />
      </section>

      <section v-if="subTasks.length || work.can_create">
        <div class="mb-2 flex items-center justify-between">
          <h3 class="text-base font-semibold text-ink-gray-9">{{ __("Child Tasks") }}</h3>
          <span v-if="subTasks.length" class="text-sm tabular-nums text-ink-gray-5">{{ __("{0} of {1}", [subTasks.filter((one) => one.status === "Completed").length, subTasks.length]) }}</span>
        </div>
        <div class="flex flex-col gap-1.5">
          <button v-for="one in subTasks" :key="one.name" class="flex min-w-0 items-center gap-2 text-start text-base hover:underline" @click="$emit('open', one.name)">
            <span class="lucide-circle-check size-4 shrink-0" :class="one.status === 'Completed' ? 'text-ink-green-3' : 'text-ink-gray-4'" />
            <span class="truncate" :class="one.status === 'Completed' ? 'text-ink-gray-5 line-through' : 'text-ink-gray-8'">{{ one.subject }}</span>
          </button>
        </div>
        <TextInput v-if="work.can_create" v-model="newSub" size="sm" class="mt-2" :placeholder="__('Add Sub-task')" @keydown.enter="addSub" />
      </section>

      <section>
        <h3 class="mb-2 text-base font-semibold text-ink-gray-9">{{ __("Activity") }}</h3>
        <Activity :key="task.name" doctype="Task" :name="task.name" />
      </section>
    </div>
  </Drawer>
</template>

<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from "vue";
import { Button, Checkbox, Dropdown, Switch, TextInput } from "frappe-ui";

import { Drawer, People, Pill, __, call, can, go, hours, listen, onedesk } from "../kit";
import { PRIORITY, TASK_STATUS } from "./colors";
import Due from "./Due.vue";

const Activity = defineAsyncComponent(() => import("./Activity.vue"));

const props = defineProps({ task: Object, work: { type: Object, required: true }, team: Array, canWrite: Boolean });
const emit = defineEmits(["close", "set", "give", "take", "open", "add", "changed"]);
const LINK = "text-ink-gray-8 underline decoration-outline-gray-3 underline-offset-4 hover:decoration-ink-gray-8";

const doc = ref(null);
const repeat = ref(null);
async function load() {
  const name = props.task?.name;
  if (!name) return (doc.value = null);
  const got = await call("frappe.client.get", { doctype: "Task", name });
  if (props.task?.name !== name) return;
  doc.value = got;
  repeat.value = got.auto_repeat ? await call("onedesk.one_task.task.repeat_of", { task: name }) : null;
}
watch(() => [props.task?.name, props.task?.modified], load, { immediate: true });

const steps = computed(() => doc.value?.one_steps || []);
const subTasks = computed(() => (props.task ? props.work.tasks.filter((one) => one.parent_task === props.task.name) : []));
const subject = (name) => props.work.tasks.find((one) => one.name === name)?.subject || name;
const waits = computed(() =>
  (doc.value?.depends_on || []).map((row) => {
    const known = props.work.tasks.find((one) => one.name === row.task);
    const subject = known?.subject || row.subject || row.task;
    return { name: row.task, subject, done: known ? ["Completed", "Cancelled"].includes(known.status) : !props.task?.waiting?.includes(subject) };
  })
);

const newStep = ref("");
const newSub = ref("");
async function tick(step, done) {
  step.done = done ? 1 : 0;
  await call("onedesk.one_task.task.tick", { task: props.task.name, step: step.name, done: done ? 1 : 0 });
  emit("changed");
}
async function addStep() {
  const text = newStep.value.trim();
  if (!text) return;
  newStep.value = "";
  await call("onedesk.one_task.task.add_step", { task: props.task.name, step: text });
  await load();
  emit("changed");
}
function addSub() {
  const text = newSub.value.trim();
  if (!text) return;
  newSub.value = "";
  emit("add", props.task.project, text, { parent_task: props.task.name });
}

const canTime = computed(() => can("create", "Timesheet"));
const running = ref(null);
const timing = computed(() => running.value?.task === props.task?.name);
const timed = async () => {
  if (props.task?.name && canTime.value) running.value = await call("onedesk.one_task.timer.running");
};
watch(() => props.task?.name, timed, { immediate: true });
onBeforeUnmount(listen("one_timers", timed));
async function time() {
  if (timing.value) {
    const added = await call("onedesk.one_task.timer.stop");
    onedesk().task_timer?.stopped?.(added);
    running.value = null;
  } else {
    running.value = await call("onedesk.one_task.timer.start", { task: props.task.name });
  }
}

const details = () => onedesk().project.task_details(props.task.name, doc.value?.modified || props.task.modified, () => emit("changed"));
const menu = computed(() =>
  [
    props.canWrite && { label: __("Edit Details"), icon: "lucide-pencil", onClick: details },
    props.canWrite && !doc.value?.auto_repeat && { label: __("Repeat"), icon: "lucide-repeat", onClick: () => onedesk().project.repeat_task(props.task.name, () => (load(), emit("changed"))) },
    props.canWrite && doc.value?.auto_repeat && !repeat.value?.disabled && { label: __("Stop Repeating"), icon: "lucide-repeat", onClick: () => onedesk().project.stop_repeat(props.task.name, load) },
    { label: __("Open Task"), icon: "lucide-external-link", onClick: () => go(`/desk/task/${props.task.name}`) },
  ].filter(Boolean)
);
</script>
