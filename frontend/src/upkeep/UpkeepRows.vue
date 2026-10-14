<template>
  <!-- Upkeep's tabs as tables, modelled on UpKeep's and Fiix's work order
       lists: each row the asset with its picture and the job, one status,
       who does it and when (one_inventory/upkeep.py). Planned, Asset Repair,
       Asset Maintenance and Completed each have the columns their rows need. -->
  <p v-if="!rows.length && empty" class="py-6 text-base text-ink-gray-5">{{ empty }}</p>

  <!-- Services not done yet. -->
  <List v-else-if="kind === 'due'" :columns="DUE" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
    <ListHeader>
      <ListHeaderCell>{{ __("Asset") }}</ListHeaderCell>
      <ListHeaderCell class="max-sm:hidden">{{ __("Status") }}</ListHeaderCell>
      <ListHeaderCell class="max-lg:hidden">{{ __("Who") }}</ListHeaderCell>
      <ListHeaderCell class="max-xl:hidden">{{ __("Periodicity") }}</ListHeaderCell>
      <ListHeaderCell>{{ __("Due") }}</ListHeaderCell>
      <ListHeaderCell />
    </ListHeader>
    <ListRows :items="rows" row-key="name" v-slot="{ item }">
      <ListRow @click="go(`/desk/asset-maintenance-log/${encodeURIComponent(item.name)}`)">
        <ListCell class="min-w-0 gap-3">
          <Avatar :label="item.asset_name" :image="item.image" shape="square" size="lg" />
          <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate text-base font-medium text-ink-gray-8">{{ item.asset_name }}</span>
            <div class="flex min-w-0 items-center gap-2">
              <Badge :label="dueState(item).label" :theme="dueState(item).theme" size="sm" class="sm:hidden" />
              <span class="truncate text-sm text-ink-gray-5">{{ item.task_name }}</span>
            </div>
          </div>
        </ListCell>
        <ListCell class="max-sm:hidden"><Badge :label="dueState(item).label" :theme="dueState(item).theme" size="md" /></ListCell>
        <ListCell class="min-w-0 gap-2 max-lg:hidden">
          <template v-if="item.assign_to_name">
            <Avatar :label="item.assign_to_name" size="sm" />
            <span class="truncate text-base text-ink-gray-7">{{ item.assign_to_name }}</span>
          </template>
          <span v-else class="text-base text-ink-gray-4">–</span>
        </ListCell>
        <ListCell class="text-base text-ink-gray-7 max-xl:hidden">{{ item.periodicity ? __(item.periodicity) : "–" }}</ListCell>
        <ListCell><When :day="item.due_date" :late="item.late" /></ListCell>
        <ListCell class="justify-end" @click.stop>
          <Dropdown :options="dueMenu(item)" placement="right">
            <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
          </Dropdown>
        </ListCell>
      </ListRow>
    </ListRows>
  </List>

  <!-- What broke. -->
  <List v-else-if="kind === 'repairs'" :columns="REPAIRS" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
    <ListHeader>
      <ListHeaderCell>{{ __("Asset") }}</ListHeaderCell>
      <ListHeaderCell class="max-sm:hidden">{{ __("Status") }}</ListHeaderCell>
      <ListHeaderCell class="max-lg:hidden">{{ __("Failure Date") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end">{{ __("Downtime") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end max-md:hidden">{{ __("Cost") }}</ListHeaderCell>
    </ListHeader>
    <ListRows :items="rows" row-key="name" v-slot="{ item }">
      <ListRow @click="go(`/desk/asset-repair/${encodeURIComponent(item.name)}`)">
        <ListCell class="min-w-0 gap-3">
          <Avatar :label="item.asset_name" :image="item.image" shape="square" size="lg" />
          <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate text-base font-medium text-ink-gray-8">{{ item.asset_name }}</span>
            <div class="flex min-w-0 items-center gap-2">
              <Badge :label="repairState(item).label" :theme="repairState(item).theme" size="sm" class="sm:hidden" />
              <span class="truncate text-sm text-ink-gray-5">{{ item.description || item.name }}</span>
            </div>
          </div>
        </ListCell>
        <ListCell class="max-sm:hidden"><Badge :label="repairState(item).label" :theme="repairState(item).theme" size="md" /></ListCell>
        <ListCell class="whitespace-nowrap text-base tabular-nums text-ink-gray-7 max-lg:hidden">{{ item.failure_date ? date(item.failure_date.slice(0, 10)) : "–" }}</ListCell>
        <ListCell class="justify-end whitespace-nowrap text-base tabular-nums" :class="item.open ? 'text-ink-red-5' : 'text-ink-gray-7'">
          {{ item.days_out === null ? "–" : item.days_out === 1 ? __("1 day") : __("{0} days", [count(item.days_out)]) }}
        </ListCell>
        <ListCell class="justify-end whitespace-nowrap text-base tabular-nums text-ink-gray-7 max-md:hidden">{{ item.repair_cost ? money(item.repair_cost, currency) : "–" }}</ListCell>
      </ListRow>
    </ListRows>
  </List>

  <!-- Each asset's plan. -->
  <List v-else-if="kind === 'plans'" :columns="PLANS" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
    <ListHeader>
      <ListHeaderCell>{{ __("Asset") }}</ListHeaderCell>
      <ListHeaderCell class="max-md:hidden">{{ __("Maintenance Tasks") }}</ListHeaderCell>
      <ListHeaderCell class="max-lg:hidden">{{ __("Maintenance Team") }}</ListHeaderCell>
      <ListHeaderCell>{{ __("Next Due Date") }}</ListHeaderCell>
    </ListHeader>
    <ListRows :items="rows" row-key="name" v-slot="{ item }">
      <ListRow @click="go(`/desk/asset-maintenance/${encodeURIComponent(item.name)}`)">
        <ListCell class="min-w-0 gap-3">
          <Avatar :label="item.asset_name" :image="item.image" shape="square" size="lg" />
          <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate text-base font-medium text-ink-gray-8">{{ item.asset_name }}</span>
            <span class="truncate text-sm text-ink-gray-5">{{ item.manager ? __("Managed by {0}", [item.manager]) : item.asset }}</span>
          </div>
        </ListCell>
        <ListCell class="max-md:hidden">
          <div class="flex min-w-0 flex-col">
            <span class="truncate text-base text-ink-gray-7">{{ item.tasks.map((job) => job.task).join(", ") || "–" }}</span>
            <span v-if="item.tasks.length" class="truncate text-sm text-ink-gray-5">{{ item.tasks.map((job) => __(job.periodicity || "")).filter(Boolean).join(", ") }}</span>
          </div>
        </ListCell>
        <ListCell class="truncate text-base text-ink-gray-7 max-lg:hidden">{{ item.team || "–" }}</ListCell>
        <ListCell><When :day="item.next" :late="item.next && item.next < today()" /></ListCell>
      </ListRow>
    </ListRows>
  </List>

  <!-- What was done. -->
  <List v-else :columns="DONE" divider="full" :row-height="56" class="-mx-3 list-gap-4 list-row-px-3">
    <ListHeader>
      <ListHeaderCell>{{ __("Asset") }}</ListHeaderCell>
      <ListHeaderCell class="max-sm:hidden">{{ __("Kind") }}</ListHeaderCell>
      <ListHeaderCell class="max-lg:hidden">{{ __("By") }}</ListHeaderCell>
      <ListHeaderCell class="justify-end max-md:hidden">{{ __("Cost") }}</ListHeaderCell>
      <ListHeaderCell>{{ __("Completion Date") }}</ListHeaderCell>
    </ListHeader>
    <ListRows :items="rows" row-key="name" v-slot="{ item }">
      <ListRow @click="go(item.kind === 'repair' ? `/desk/asset-repair/${encodeURIComponent(item.name)}` : `/desk/asset-maintenance-log/${encodeURIComponent(item.name)}`)">
        <ListCell class="min-w-0 gap-3">
          <Avatar :label="item.asset_name" shape="square" size="lg" />
          <div class="flex min-w-0 flex-col gap-1">
            <span class="truncate text-base font-medium text-ink-gray-8">{{ item.asset_name }}</span>
            <span class="truncate text-sm text-ink-gray-5">{{ [item.what, item.notes].filter(Boolean).join(" · ") }}</span>
          </div>
        </ListCell>
        <ListCell class="max-sm:hidden">
          <Badge :label="item.kind === 'repair' ? __('Repair') : __('Maintenance')" :theme="item.kind === 'repair' ? 'amber' : 'blue'" size="md" />
        </ListCell>
        <ListCell class="truncate text-base text-ink-gray-7 max-lg:hidden">{{ item.by || "–" }}</ListCell>
        <ListCell class="justify-end whitespace-nowrap text-base tabular-nums text-ink-gray-7 max-md:hidden">{{ item.cost ? money(item.cost, currency) : "–" }}</ListCell>
        <ListCell class="whitespace-nowrap text-base tabular-nums text-ink-gray-7">{{ item.on ? date(item.on) : "–" }}</ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { defineComponent, h } from "vue";
import { Avatar, Badge, Button, Dropdown } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { __, count, date, fromToday, go, money, onedesk, today } from "../kit";

const props = defineProps({
  kind: { type: String, required: true },
  rows: { type: Array, required: true },
  can: { type: Object, required: true },
  currency: String,
  empty: String,
});
const emit = defineEmits(["changed"]);

// A day and how far it is from today, red once past.
const When = defineComponent({
  props: { day: String, late: Boolean },
  setup: (p) => () =>
    p.day
      ? h("div", { class: "flex flex-col" }, [
          h("span", { class: "whitespace-nowrap text-base tabular-nums text-ink-gray-7" }, date(p.day)),
          h("span", { class: ["whitespace-nowrap text-sm", p.late ? "text-ink-red-5" : "text-ink-gray-5"] }, fromToday(p.day)),
        ])
      : h("span", { class: "text-base text-ink-gray-4" }, "–"),
});

// Each table keeps the asset and the day on a phone; the rest join as it widens.
const DUE = {
  base: ["minmax(0,1fr)", "7rem", "2rem"],
  sm: ["minmax(0,1fr)", "7rem", "8rem", "2rem"],
  lg: ["minmax(0,1fr)", "7rem", "minmax(0,12rem)", "8rem", "2rem"],
  xl: ["minmax(0,1fr)", "7rem", "minmax(0,12rem)", "7rem", "8rem", "2rem"],
};
const REPAIRS = {
  base: ["minmax(0,1fr)", "6rem"],
  sm: ["minmax(0,1fr)", "8rem", "6rem"],
  md: ["minmax(0,1fr)", "8rem", "6rem", "8rem"],
  lg: ["minmax(0,1fr)", "8rem", "7rem", "6rem", "8rem"],
};
const PLANS = {
  base: ["minmax(0,1fr)", "8rem"],
  md: ["minmax(0,1fr)", "minmax(0,1fr)", "8rem"],
  lg: ["minmax(0,1fr)", "minmax(0,1fr)", "minmax(0,10rem)", "8rem"],
};
const DONE = {
  base: ["minmax(0,1fr)", "7rem"],
  sm: ["minmax(0,1fr)", "6rem", "7rem"],
  md: ["minmax(0,1fr)", "6rem", "7rem", "7rem"],
  lg: ["minmax(0,1fr)", "6rem", "minmax(0,10rem)", "7rem", "7rem"],
};

// A service late, due within a week, or further off.
function dueState(one) {
  if (one.late) return { label: __("Overdue"), theme: "red" };
  const soon = one.due_date && (new Date(one.due_date) - new Date(today())) / 86400000 <= 7;
  return soon ? { label: __("Due Soon"), theme: "amber" } : { label: __("Planned"), theme: "gray" };
}
const repairState = (one) => (one.open ? { label: __("Out of Order"), theme: "red" } : { label: __("Completed"), theme: "green" });

const dueMenu = (one) =>
  [
    props.can.done && { label: __("Mark Done"), icon: "lucide-check", onClick: () => onedesk().upkeep.done(one.name, one.asset_name, () => emit("changed")) },
    { label: __("Open Asset"), icon: "lucide-arrow-up-right", onClick: () => go(`/desk/asset/${encodeURIComponent(one.asset)}`) },
  ].filter(Boolean);
</script>
