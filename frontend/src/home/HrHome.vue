<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <div v-if="cards.length" ref="cardsRoot" class="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <NumberCard v-for="card in cards" :key="card.key" v-bind="card.props" class="cursor-pointer" role="link" @click="go(card.route)" />
      </div>
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <template v-if="shown === 'overview'">
        <Loading v-if="!story" />
        <HrStory v-else :story="story" :needs="chips" @today="shown = 'today'" />
      </template>

      <template v-else-if="shown === 'today'">
        <p v-if="!parts.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Nothing needs you") }}</p>
        <Section v-for="part in parts" :key="part.key" :title="part.title" :icon="part.icon" :aside="part.count">
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
            <li v-for="one in group.rows" :key="one.label">
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
import { NumberCard, useChartTokens } from "frappe-ui/charts";

import { Loading, Page, PlaceSpot, Rows, Section, ViewTabs, __, ago, call, date, followList, go, money, newDoc, onedesk, setQuery } from "../kit";
import HrStory from "./HrStory.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const shown = ref(props.route[0] || props.query.view || null);
const search = ref("");
const story = ref(null);
const clock = ref(null);

async function load() {
  call("onedesk.one_hr.story.read").then((got) => (story.value = got));
  clock.value = await call("onedesk.one_hr.clock.ready");
  said.value = await call("onedesk.one_hr.home.read");
  if (!shown.value) shown.value = said.value.hr ? "overview" : "today";
  report();
}
load();

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 800);
};
const stop = [
  "Leave Application",
  "Leave Allocation",
  "Leave Period",
  "Expense Claim",
  "Shift Request",
  "Attendance Request",
  "Attendance",
  "Clock Attempt",
  "Employee Checkin",
  "Interview",
  "Employee",
  "Salary Slip",
  "Job Opening",
  "Job Applicant",
  "Job Offer",
].map((one) => followList(one, soon));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => setQuery("view", now === (said.value?.hr ? "overview" : "today") ? null : now));

const views = computed(() => [
  ...(said.value.hr ? [{ key: "overview", label: __("Overview") }] : []),
  { key: "today", label: __("Today"), count: needed.value || null },
  { key: "everything", label: __("Everything") },
  ...said.value.groups.filter((one) => ["reports", "setup"].includes(one.key) && said.value.everything.some((row) => row.group === one.key)).map((one) => ({ key: one.key, label: one.label })),
]);

const KINDS = ["mine", "approve", "flagged", "expiring", "ending", "interviews"];
const needed = computed(() => {
  const n = said.value?.needs;
  return n ? KINDS.reduce((sum, key) => sum + n[key].count, 0) : 0;
});

const CARDS = () => [
  { key: "headcount", title: __("Headcount"), plain: true, type: "line", hue: 0, route: "/desk/employee?status=Active" },
  { key: "joined", title: __("Joined This Month"), plain: true, type: "bar", hue: 2, route: "/desk/employee?status=Active" },
  { key: "present", title: __("Present Today"), plain: true, route: "/desk/attendance" },
  { key: "away", title: __("On Leave Today"), plain: true, route: '/desk/leave-application?status=Approved' },
  { key: "payroll", title: __("Last Payroll"), type: "bar", hue: 4, route: "/desk/query-report/Salary Register" },
  { key: "openings", title: __("Open Positions"), plain: true, route: "/desk/job-opening?status=Open" },
];
const cardsRoot = ref();
const { tokens } = useChartTokens(cardsRoot);
const change = (series, plain) => {
  const [before, now] = (series || []).slice(-2);
  if (plain) return series?.length > 1 ? now - before : null;
  return before ? Math.round(((now - before) / Math.abs(before)) * 100) : null;
};
const format = (one) => (value) => (one.plain ? String(value) : money(value, story.value.currency, 0));
const cards = computed(() => {
  const hues = tokens.value.categorical;
  const leave = (said.value?.needs?.leave || []).map((one) => ({
    key: `leave-${one.leave_type}`,
    route: "/desk/leave-application/new",
    props: { title: __("{0} Left", [one.label]), value: one.left, format: (value) => __("{0} of {1} days", [value, one.given]) },
  }));
  if (!story.value?.cards) return leave;
  const got = story.value.cards;
  return CARDS()
    .filter((one) => got[one.key])
    .map((one) => ({
      key: one.key,
      route: one.route,
      props: {
        title: one.title,
        value: got[one.key].value ?? 0,
        format: format(one),
        ...(got[one.key].series && change(got[one.key].series, one.plain) !== null ? { delta: change(got[one.key].series, one.plain), deltaSuffix: one.plain ? "" : "%", deltaCaption: __("vs last month") } : {}),
        ...(got[one.key].series ? { sparkline: { data: got[one.key].series, type: one.type, color: hues[one.hue] || undefined } } : {}),
      },
    }));
});

const chips = computed(() => {
  const n = said.value?.needs;
  if (!n) return [];
  return [
    n.approve.count && { key: "approve", tone: "soon", icon: "lucide-inbox", label: n.approve.count === 1 ? __("1 Request Waiting for You") : __("{0} Requests Waiting for You", [n.approve.count]) },
    n.flagged.count && { key: "flagged", tone: "late", icon: "lucide-flag", label: n.flagged.count === 1 ? __("1 Check-in Flagged") : __("{0} Check-ins Flagged", [n.flagged.count]) },
    n.expiring.count && { key: "expiring", tone: "soon", icon: "lucide-id-card", label: n.expiring.count === 1 ? __("1 Document Expiring") : __("{0} Documents Expiring", [n.expiring.count]) },
    n.ending.count && { key: "ending", tone: "soon", icon: "lucide-calendar-clock", label: n.ending.count === 1 ? __("1 Contract or Probation Ending") : __("{0} Contracts or Probations Ending", [n.ending.count]) },
    n.interviews.count && { key: "interviews", tone: "left", icon: "lucide-users", label: n.interviews.count === 1 ? __("1 Interview Today") : __("{0} Interviews Today", [n.interviews.count]) },
  ].filter(Boolean);
});

const ICONS = { DocType: "lucide-list", Report: "lucide-chart-column", Page: "lucide-layout-panel-top", List: "lucide-tags" };

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
  const sections = said.value.sections?.[shown.value];
  if (sections)
    return sections
      .map((topic) => ({ ...topic, rows: said.value.everything.filter((one) => one.group === shown.value && one.topic === topic.key && matches(one)) }))
      .filter((topic) => topic.rows.length);
  return said.value.groups
    .map((group) => ({ ...group, rows: said.value.everything.filter((one) => one.group === group.key && matches(one)) }))
    .filter((group) => group.rows.length);
});

const open = (one) => `/desk/${slug(one.doctype)}/${encodeURIComponent(one.name)}`;
const dates = (one) => (one.from ? (one.to && one.to !== one.from ? `${date(one.from)} – ${date(one.to)}` : date(one.from)) : "");
const requests = (rows, mine) =>
  rows.map((one) => ({
    key: `${one.doctype}-${one.name}`,
    label: mine ? __(one.doctype) : one.who,
    sub: mine ? one.about : `${__(one.doctype)} · ${one.about}`,
    dot: "amber",
    value: dates(one),
    under: __("Asked {0}", [ago(one.since)]),
    route: open(one),
  }));
const due = (days) => (days === 0 ? __("Today") : days === 1 ? __("Tomorrow") : __("In {0} days", [days]));
const dated = (rows) => rows.map((one) => ({ key: `${one.name}-${one.about}`, label: one.who, sub: one.about, dot: one.days <= 7 ? "red" : "amber", value: date(one.on), under: due(one.days), route: open(one) }));

const parts = computed(() => {
  const n = said.value.needs;
  const more = (kept, label, where) => (kept.count > kept.rows.length ? { label: __("{0} more", [kept.count - kept.rows.length]) + " · " + label, route: where } : null);
  const out = [];
  if (n.approve.count)
    out.push({ key: "approve", title: __("Waiting for You"), icon: "lucide-inbox", count: n.approve.count, rows: requests(n.approve.rows, false), more: more(n.approve, __("Leave Application"), "/desk/leave-application?status=Open") });
  if (n.mine.count) out.push({ key: "mine", title: __("Your Requests"), icon: "lucide-hourglass", count: n.mine.count, rows: requests(n.mine.rows, true) });
  if (n.flagged.count)
    out.push({
      key: "flagged",
      title: __("Check-ins Flagged"),
      icon: "lucide-flag",
      count: n.flagged.count,
      rows: n.flagged.rows.map((one) => ({ key: one.name, label: one.who, sub: one.about, dot: "red", under: ago(one.since), route: open(one) })),
      more: more(n.flagged, __("Clock Attempt"), "/desk/clock-attempt?outcome=Flagged"),
    });
  if (n.expiring.count) out.push({ key: "expiring", title: __("Documents Expiring"), icon: "lucide-id-card", count: n.expiring.count, rows: dated(n.expiring.rows) });
  if (n.ending.count) out.push({ key: "ending", title: __("Contracts and Probations Ending"), icon: "lucide-calendar-clock", count: n.ending.count, rows: dated(n.ending.rows) });
  if (n.interviews.count)
    out.push({ key: "interviews", title: __("Interviews Today"), icon: "lucide-users", count: n.interviews.count, rows: n.interviews.rows.map((one) => ({ key: one.name, label: one.who, sub: one.about, dot: "gray", value: one.at, route: open(one) })) });
  return out;
});

function checkLabel(direction) {
  if (direction === "OUT") return __("Check Out");
  const due = clock.value?.due && clock.value.state !== "in" ? onedesk().clock.time(clock.value.due) : "";
  if (due && clock.value.late) return __("Check In (late)");
  return due ? __("Check in by {0}", [due]) : __("Check In");
}

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("OneHR") });
  extended(s);
  const direction = clock.value?.direction;
  props.onActions?.([
    ...(direction ? [{ label: checkLabel(direction), primary: true, onClick: () => onedesk().dock.punch().then(load) }] : []),
    { label: __("Request Leave"), primary: !direction, onClick: () => newDoc("Leave Application") },
    { label: __("Claim an Expense"), onClick: () => newDoc("Expense Claim") },
  ]);
}

const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("onehr_home.shown")) return;
  const n = s.needs;
  const data = { home: Object.fromEntries(KINDS.map((key) => [key, n[key].count])) };
  const now = JSON.stringify(data);
  if (now === drawn) return;
  drawn = now;
  placed.notes = [];
  placed.actions = [];
  places.emit("onehr_home.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
