<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <div v-if="cards.length" data-tour="onequality-figures" class="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4 [&_.truncate]:whitespace-normal">
        <NumberCard v-for="card in cards" :key="card.key" v-bind="card.props" class="cursor-pointer" role="link" @click="go(card.route)" />
      </div>
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" data-tour="onequality-home-views" />

      <template v-if="shown === 'today'">
        <p v-if="!parts.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Nothing needs you") }}</p>
        <Section v-for="part in parts" :key="part.key" :title="part.title" :icon="part.icon" :aside="part.count" :action="part.action">
          <Rows :rows="part.rows" />
          <button v-if="part.more" type="button" class="mt-2 text-sm text-ink-gray-5 hover:underline" @click="go(part.more.route)">{{ part.more.label }}</button>
        </Section>
      </template>

      <template v-else>
        <TextInput v-model="search" class="mt-4 w-full max-w-xs" type="search" :placeholder="__('Search')" :aria-label="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
        <p v-if="!groups.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Nothing matches") }}</p>
        <Section v-for="group in groups" :key="group.key" :title="group.label" :aside="group.rows.length">
          <ul class="grid grid-cols-1 gap-x-6 sm:grid-cols-2 xl:grid-cols-3">
            <li v-for="one in group.rows" :key="one.target">
              <button type="button" class="flex w-full items-start gap-3 rounded-3 px-2 py-2.5 text-start hover:bg-surface-gray-2 focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(route(one))">
                <span :class="ICONS[one.kind]" class="mt-0.5 size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
                <span class="min-w-0">
                  <span class="block truncate text-base text-ink-gray-8">{{ one.label }}</span>
                  <span class="block text-sm text-ink-gray-5">{{ one.about }}</span>
                </span>
              </button>
            </li>
          </ul>
        </Section>
      </template>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { TextInput } from "frappe-ui";
import { NumberCard } from "frappe-ui/charts";

import { Loading, Page, PlaceSpot, Rows, Section, ViewTabs, __, ago, call, can, count, date, followList, go, newDoc, onedesk, setQuery, shortcut } from "../kit";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const wanted = () => props.query.view || props.route[0] || "today";
const shown = ref(wanted());
watch(
  () => [props.route[0], props.query.view],
  () => wanted() !== shown.value && (shown.value = wanted())
);
const search = ref("");

async function load() {
  said.value = await call("onedesk.one_quality.home.read");
  report();
}
load();

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 800);
};
const stop = ["Non Conformance", "Quality Action", "Quality Review", "Quality Goal", "Quality Meeting"].map((one) => followList(one, soon));
const keyed = (doctype) => () => can("create", doctype) && newDoc(doctype);
const forgetKeys = [shortcut("one_quality.report_problem", keyed("Non Conformance")), shortcut("one_quality.new_action", keyed("Quality Action"))];
onBeforeUnmount(() => forgetKeys.forEach((one) => one()));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => setQuery("view", now === (props.route[0] || "today") ? null : now));

const views = computed(() => [
  { key: "today", label: __("Today"), count: needed.value || null },
  { key: "everything", label: __("Everything") },
  ...said.value.groups.filter((one) => ["reports", "setup"].includes(one.key) && said.value.everything.some((row) => row.group === one.key)).map((one) => ({ key: one.key, label: one.label })),
]);

const needed = computed(() => {
  const n = said.value?.needs;
  if (!n) return 0;
  return n.problems.count + n.late.count + n.failing.count + n.meetings.count;
});

const CARDS = () => [
  { key: "problems", title: __("Open Non Conformances"), route: "/desk/non-conformance?status=Open" },
  { key: "actions", title: __("Open Actions"), route: "/desk/quality-action?status=Open" },
  { key: "late", title: __("Steps Overdue"), route: "/desk/quality-action?status=Open" },
  { key: "failing", title: __("Goals Failing"), route: "/desk/quality-review?status=Failed" },
];
const cards = computed(() => {
  const got = said.value?.figures || {};
  return CARDS()
    .filter((one) => got[one.key] !== null && got[one.key] !== undefined)
    .map((one) => ({ key: one.key, route: one.route, props: { title: one.title, value: got[one.key] ?? 0, format: count } }));
});

const ICONS = { DocType: "lucide-list", Report: "lucide-chart-column", Page: "lucide-layout-panel-top" };

function slug(doctype) {
  return doctype.toLowerCase().replace(/ /g, "-");
}

function route(one) {
  if (one.kind === "Report") return `/desk/query-report/${encodeURIComponent(one.target)}`;
  if (one.kind === "Page") return `/desk/${one.target}`;
  return `/desk/${slug(one.target)}`;
}

const groups = computed(() => {
  const words = search.value.trim().toLowerCase();
  const matches = (one) => !words || `${one.label} ${one.about}`.toLowerCase().includes(words);
  const only = ["reports", "setup"].includes(shown.value) ? shown.value : null;
  return said.value.groups
    .filter((group) => !only || group.key === only)
    .map((group) => ({ ...group, rows: said.value.everything.filter((one) => one.group === group.key && matches(one)) }))
    .filter((group) => group.rows.length);
});

const parts = computed(() => {
  const n = said.value.needs;
  const more = (kept, label, where) => (kept.count > kept.rows.length ? { label: __("{0} more", [kept.count - kept.rows.length]) + " · " + label, route: where } : null);
  const out = [];
  if (n.problems.count)
    out.push({
      key: "problems",
      title: __("Open Non Conformances"),
      icon: "lucide-triangle-alert",
      count: n.problems.count,
      rows: n.problems.rows.map((one) => ({
        key: one.name,
        label: one.subject,
        sub: one.procedure || "",
        dot: one.actions ? "amber" : "red",
        below: one.actions ? (one.actions === 1 ? __("1 action") : __("{0} actions", [one.actions])) : __("No action yet"),
        value: one.raised_by,
        under: __("Raised {0}", [ago(one.creation)]),
        route: `/desk/non-conformance/${encodeURIComponent(one.name)}`,
      })),
      more: more(n.problems, __("Non Conformance"), "/desk/non-conformance?status=Open"),
    });
  if (n.late.count)
    out.push({
      key: "late",
      title: __("Steps Overdue"),
      icon: "lucide-clock-alert",
      count: n.late.count,
      rows: n.late.rows.map((one, at) => ({
        key: `${one.action}-${at}`,
        label: one.problem,
        sub: one.action,
        dot: "red",
        below: one.who || __("Nobody responsible"),
        value: one.late_by === 1 ? __("1 day late") : __("{0} days late", [one.late_by]),
        under: __("Due {0}", [date(one.due)]),
        route: `/desk/quality-action/${encodeURIComponent(one.action)}`,
      })),
    });
  if (n.failing.count)
    out.push({
      key: "failing",
      title: __("Goals Failing"),
      icon: "lucide-target",
      count: n.failing.count,
      rows: n.failing.rows.map((one) => ({
        key: one.goal,
        label: one.label,
        sub: one.procedure || "",
        dot: "red",
        value: __("Failed {0}", [date(one.date)]),
        route: `/desk/quality-review/${encodeURIComponent(one.review)}`,
      })),
    });
  if (n.meetings.count)
    out.push({
      key: "meetings",
      title: __("Meetings Still Open"),
      icon: "lucide-users",
      count: n.meetings.count,
      rows: n.meetings.rows.map((one) => ({
        key: one.name,
        label: one.about || one.name,
        sub: one.about ? one.name : "",
        dot: "gray",
        value: __("Opened {0}", [ago(one.creation)]),
        route: `/desk/quality-meeting/${encodeURIComponent(one.name)}`,
      })),
    });
  return out;
});

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("OneQuality") });
  extended(s);
  const may = (doctype) => (s.may_make || []).includes(doctype);
  const made = [
    may("Non Conformance") && { label: __("Report a Problem"), onClick: () => newDoc("Non Conformance") },
    may("Quality Action") && { label: __("New Quality Action"), onClick: () => newDoc("Quality Action") },
    may("Quality Review") && { label: __("New Quality Review"), onClick: () => newDoc("Quality Review") },
  ].filter(Boolean);
  if (made.length) made[0].primary = true;
  props.onActions?.(made);
}

const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("onequality_home.shown")) return;
  const n = s.needs;
  const data = { home: { problems: n.problems.count, late: n.late.count, failing: n.failing.count, meetings: n.meetings.count } };
  const key = JSON.stringify(data);
  if (key === drawn) return;
  drawn = key;
  placed.notes = [];
  placed.actions = [];
  places.emit("onequality_home.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
