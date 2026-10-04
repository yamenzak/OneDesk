<template>
  <!-- A task opened beside the page: its fields changed in place, what it is
       about, and its comments and history. The full form is one click away. -->
  <Drawer :open="Boolean(task)" :title="task?.subject" @close="$emit('close')">
    <template #head>
      <Pill v-if="task" :value="task.status" :options="work.statuses" :colors="TASK_STATUS" :label="__('Status')" :readonly="!canWrite" @change="(v) => $emit('set', task.name, 'status', v)" />
    </template>
    <template #actions>
      <Button v-if="task" variant="ghost" icon="lucide-external-link" :aria-label="__('Open Full Form')" @click="go(`/desk/task/${task.name}`)" />
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
        <dt class="text-ink-gray-5">{{ __("Owner") }}</dt>
        <dd><People :users="task.assigned" :people="work.people" :options="canWrite ? team : null" @add="(u) => $emit('give', task.name, u)" @remove="(u) => $emit('take', task.name, u)" /></dd>
        <dt class="text-ink-gray-5">{{ __("Priority") }}</dt>
        <dd><Pill :value="task.priority" :options="work.priorities" :colors="PRIORITY" :label="__('Priority')" :readonly="!canWrite" @change="(v) => $emit('set', task.name, 'priority', v)" /></dd>
        <dt class="text-ink-gray-5">{{ __("Starts") }}</dt>
        <dd><Due :value="task.exp_start_date" done :readonly="!canWrite" @change="(v) => $emit('set', task.name, 'exp_start_date', v)" /></dd>
        <dt class="text-ink-gray-5">{{ __("Due") }}</dt>
        <dd><Due :value="task.exp_end_date" :done="task.status === 'Completed'" :readonly="!canWrite" @change="(v) => $emit('set', task.name, 'exp_end_date', v)" /></dd>
        <dt class="text-ink-gray-5">{{ __("Project") }}</dt>
        <dd class="truncate text-ink-gray-8">{{ work.groups.find((g) => g.key === task.project)?.title }}</dd>
        <dt v-if="task.expected_time || task.actual_time" class="text-ink-gray-5">{{ __("Hours") }}</dt>
        <dd v-if="task.expected_time || task.actual_time" class="text-ink-gray-8">{{ __("{0} of {1}", [hours(task.actual_time), hours(task.expected_time)]) }}</dd>
      </dl>
      <section>
        <h3 class="mb-2 text-base font-semibold text-ink-gray-9">{{ __("Description") }}</h3>
        <div v-if="description" class="text-base leading-relaxed text-ink-gray-7 [&_p]:mb-2" v-html="description" />
        <button v-else class="text-base text-ink-gray-5 hover:text-ink-gray-8" @click="go(`/desk/task/${task.name}`)">{{ __("Add a description") }}</button>
      </section>
      <section>
        <h3 class="mb-2 text-base font-semibold text-ink-gray-9">{{ __("Activity") }}</h3>
        <Activity :key="task.name" doctype="Task" :name="task.name" />
      </section>
    </div>
  </Drawer>
</template>

<script setup>
import { defineAsyncComponent, ref, watch } from "vue";
import { Button } from "frappe-ui";

import { Drawer, People, Pill, __, call, go, hours } from "../kit";
import { PRIORITY, TASK_STATUS } from "./colors";
import Due from "./Due.vue";

// The timeline brings frappe-ui's editor, so it loads when first shown.
const Activity = defineAsyncComponent(() => import("./Activity.vue"));

const props = defineProps({ task: Object, work: { type: Object, required: true }, team: Array, canWrite: Boolean });
defineEmits(["close", "set", "give", "take"]);

const description = ref("");
watch(
  () => props.task?.name,
  async (name) => {
    description.value = "";
    if (!name) return;
    const got = await call("frappe.client.get_value", { doctype: "Task", filters: name, fieldname: "description" });
    if (props.task?.name === name) description.value = got?.description || "";
  },
  { immediate: true }
);
</script>
