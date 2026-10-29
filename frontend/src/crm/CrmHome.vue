<template>
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <div v-if="cards.length" ref="cardsRoot" data-tour="onecrm-figures" class="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <NumberCard v-for="card in cards" :key="card.key" v-bind="card.props" class="cursor-pointer" role="link" @click="go(card.route)" />
      </div>
      <PlaceSpot :said="placed" class="mt-4" />
      <ViewTabs v-model="shown" :views="views" class="mt-5" data-tour="onecrm-views" />

      <template v-if="shown === 'overview'">
        <Loading v-if="!story" />
        <CrmStory v-else :story="story" :needs="chips" @today="shown = 'today'" />
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

import { Loading, Page, PlaceSpot, Rows, Section, ViewTabs, __, ago, call, date, followList, go, me, money, newDoc, onedesk, setQuery } from "../kit";
import CrmStory from "./CrmStory.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
const shown = ref(props.route[0] || props.query.view || "overview");
const search = ref("");
const story = ref(null);

async function load() {
  call("onedesk.one_crm.story.read").then((got) => (story.value = got));
  said.value = await call("onedesk.one_crm.home.read");
  report();
}
load();

let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 800);
};
const stop = ["Lead", "Opportunity", "Quotation", "Sales Order"].map((one) => followList(one, soon));
onBeforeUnmount(() => {
  stop.forEach((one) => one());
  clearTimeout(timer);
});
watch(shown, (now) => setQuery("view", now === "overview" ? null : now));

const views = computed(() => [
  { key: "overview", label: __("Overview") },
  { key: "today", label: __("Today"), count: needed.value || null },
  { key: "everything", label: __("Everything") },
  ...said.value.groups.filter((one) => ["reports", "setup"].includes(one.key)).map((one) => ({ key: one.key, label: one.label })),
]);

const needed = computed(() => {
  const n = said.value?.needs;
  if (!n) return 0;
  return ["opportunities", "leads", "unplanned", "unclaimed", "closing", "expiring"].reduce((sum, key) => sum + n[key].count, 0) + n.drafts.reduce((sum, one) => sum + one.count, 0);
});

const CARDS = () => [
  { key: "leads", title: __("Leads This Month"), type: "bar", hue: 0, plain: true, route: "/desk/lead" },
  { key: "pipeline", title: __("Pipeline Value"), route: "/desk/query-report/Opportunity Forecast" },
  { key: "weighted", title: __("Weighted Pipeline"), route: "/desk/query-report/Opportunity Forecast" },
  { key: "won", title: __("Won This Month"), type: "bar", hue: 2, route: "/desk/query-report/Won and Lost" },
  { key: "rate", title: __("Win Rate (90 Days)"), percent: true, route: "/desk/query-report/Won and Lost" },
  { key: "average", title: __("Average Won Value"), route: "/desk/query-report/Won and Lost" },
];
const cardsRoot = ref();
const { tokens } = useChartTokens(cardsRoot);
const change = (series, plain) => {
  const [before, now] = (series || []).slice(-2);
  if (plain) return series?.length > 1 ? now - before : null;
  return before ? Math.round(((now - before) / Math.abs(before)) * 100) : null;
};
const format = (one) => (value) => (one.percent ? `${Math.round(value)}%` : one.plain ? String(value) : money(value, story.value.currency, 0));
const cards = computed(() => {
  const got = story.value?.cards || {};
  const hues = tokens.value.categorical;
  return CARDS()
    .filter((one) => got[one.key])
    .map((one) => ({
      key: one.key,
      route: one.route,
      props: {
        title: one.title,
        value: got[one.key].value ?? 0,
        format: format(one),
        ...(change(got[one.key].series, one.plain) === null ? {} : { delta: change(got[one.key].series, one.plain), deltaSuffix: one.plain ? "" : "%", deltaCaption: __("vs last month") }),
        ...(got[one.key].series ? { sparkline: { data: got[one.key].series, type: one.type, color: hues[one.hue] || undefined } } : {}),
      },
    }));
});

const chips = computed(() => {
  const n = said.value?.needs;
  if (!n) return [];
  const drafts = n.drafts.reduce((sum, d) => sum + d.count, 0);
  const due = n.opportunities.count + n.leads.count;
  return [
    due && { key: "due", tone: n.opportunities.rows.some((one) => one.late) || n.leads.rows.some((one) => one.late) ? "late" : "soon", icon: "lucide-alarm-clock", label: due === 1 ? __("1 Next Step Due") : __("{0} Next Steps Due", [due]) },
    n.unclaimed.count && { key: "unclaimed", tone: "soon", icon: "lucide-hand", label: n.unclaimed.count === 1 ? __("1 Unclaimed Lead") : __("{0} Unclaimed Leads", [n.unclaimed.count]) },
    n.closing.count && { key: "closing", tone: "late", icon: "lucide-calendar-x", label: n.closing.count === 1 ? __("1 Opportunity Past Its Closing Date") : __("{0} Opportunities Past Their Closing Date", [n.closing.count]) },
    n.expiring.count && { key: "expiring", tone: "soon", icon: "lucide-hourglass", label: n.expiring.count === 1 ? __("1 Quotation Expiring") : __("{0} Quotations Expiring", [n.expiring.count]) },
    n.unplanned.count && { key: "unplanned", tone: "left", icon: "lucide-circle-dashed", label: n.unplanned.count === 1 ? __("1 With No Next Step") : __("{0} With No Next Step", [n.unplanned.count]) },
    drafts && { key: "drafts", tone: "left", icon: "lucide-file-pen-line", label: drafts === 1 ? __("1 Draft Left") : __("{0} Drafts Left", [drafts]) },
  ].filter(Boolean);
});

const ICONS = { DocType: "lucide-list", Report: "lucide-chart-column", Page: "lucide-layout-panel-top", List: "lucide-tags" };

function slug(doctype) {
  return doctype.toLowerCase().replace(/ /g, "-");
}

function route(one) {
  if (one.kind === "Report") return `/desk/query-report/${encodeURIComponent(one.target)}`;
  if (one.kind === "Page") return `/desk/${one.target}`;
  const filters = Object.entries(one.filters || {});
  if (filters.length === 1 && filters[0][0] === "name") return `/desk/${slug(one.target)}/${encodeURIComponent(filters[0][1])}`;
  const query = filters.map(([key, value]) => `${key}=${encodeURIComponent(typeof value === "object" ? JSON.stringify(value) : value)}`);
  return `/desk/${slug(one.target)}${query.length ? `?${query.join("&")}` : ""}`;
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
const when = (one) => (one.late ? __("Due {0}", [ago(one.on)]) : one.on ? __("Due today") : "");
const steps = (rows) =>
  rows.map((one) => ({
    key: one.name,
    label: one.title,
    sub: one.party,
    dot: one.late ? "red" : "amber",
    value: one.step || __("Next Step"),
    under: when(one),
    route: open(one),
  }));
const late = (days) => (days === 1 ? __("1 day past") : __("{0} days past", [days]));
const expires = (days) => (days === 0 ? __("Expires today") : days === 1 ? __("Expires tomorrow") : __("Expires in {0} days", [days]));

const parts = computed(() => {
  const n = said.value.needs;
  const more = (kept, label, where) => (kept.count > kept.rows.length ? { label: __("{0} more", [kept.count - kept.rows.length]) + " · " + label, route: where } : null);
  const out = [];
  if (n.opportunities.count)
    out.push({
      key: "opportunities",
      title: __("Opportunities Due"),
      icon: "lucide-alarm-clock",
      count: n.opportunities.count,
      rows: steps(n.opportunities.rows),
      more: more(n.opportunities, __("Opportunity"), `/desk/opportunity?opportunity_owner=${encodeURIComponent(me())}`),
    });
  if (n.leads.count)
    out.push({
      key: "leads",
      title: __("Leads Due"),
      icon: "lucide-alarm-clock",
      count: n.leads.count,
      rows: steps(n.leads.rows),
      more: more(n.leads, __("Lead"), `/desk/lead?lead_owner=${encodeURIComponent(me())}`),
    });
  if (n.closing.count)
    out.push({
      key: "closing",
      title: __("Past Expected Closing Date"),
      icon: "lucide-calendar-x",
      count: n.closing.count,
      rows: n.closing.rows.map((one) => ({ key: one.name, label: one.title, sub: one.party, dot: "red", value: date(one.closing), under: late(one.days), route: open(one) })),
      more: more(n.closing, __("Opportunity"), `/desk/opportunity?opportunity_owner=${encodeURIComponent(me())}`),
    });
  if (n.unclaimed.count)
    out.push({
      key: "unclaimed",
      title: __("Unclaimed Leads"),
      icon: "lucide-hand",
      count: n.unclaimed.count,
      rows: n.unclaimed.rows.map((one) => ({ key: one.name, label: one.title, sub: one.party, dot: "amber", value: one.source ? __(one.source) : "", under: ago(one.since), route: open(one) })),
      more: more(n.unclaimed, __("Lead"), '/desk/lead?lead_owner=["is","not set"]'),
    });
  if (n.expiring.count)
    out.push({
      key: "expiring",
      title: __("Quotations Expiring"),
      icon: "lucide-hourglass",
      count: n.expiring.count,
      rows: n.expiring.rows.map((one) => ({ key: one.name, label: one.party, sub: one.name, dot: "amber", value: money(one.grand_total, one.currency), under: expires(one.days), route: `/desk/quotation/${encodeURIComponent(one.name)}` })),
      more: more(n.expiring, __("Quotation"), "/desk/quotation?status=Open"),
    });
  if (n.unplanned.count)
    out.push({
      key: "unplanned",
      title: __("No Next Step"),
      icon: "lucide-circle-dashed",
      count: n.unplanned.count,
      rows: n.unplanned.rows.map((one) => ({ key: one.name, label: one.title, sub: one.party, dot: "gray", value: __(one.doctype), route: open(one) })),
    });
  if (n.drafts.length)
    out.push({
      key: "drafts",
      title: __("Left as Drafts"),
      icon: "lucide-file-pen-line",
      count: n.drafts.reduce((sum, one) => sum + one.count, 0),
      rows: n.drafts.map((one) => ({
        key: one.doctype,
        label: one.label,
        below: __("Started more than a day ago"),
        value: one.count === 1 ? __("1 draft") : __("{0} drafts", [one.count]),
        route: `/desk/${slug(one.doctype)}?docstatus=0`,
      })),
    });
  return out;
});

function report() {
  const s = said.value;
  props.onTitle?.({ title: __("OneCRM") });
  extended(s);
  const can = (doctype) => s.everything.some((one) => one.kind === "DocType" && one.target === doctype);
  props.onActions?.(
    [
      can("Lead") && { label: __("New Lead"), primary: true, onClick: () => newDoc("Lead") },
      can("Opportunity") && { label: __("New Opportunity"), onClick: () => newDoc("Opportunity") },
      can("Quotation") && { label: __("New Quotation"), onClick: () => newDoc("Quotation") },
    ].filter(Boolean)
  );
}

const placed = reactive({ notes: [], actions: [] });
let drawn = null;
function extended(s) {
  const places = onedesk().places;
  if (!places?.listening("onecrm_home.shown")) return;
  const n = s.needs;
  const data = { home: { due: n.opportunities.count + n.leads.count, closing: n.closing.count, unclaimed: n.unclaimed.count, expiring: n.expiring.count, unplanned: n.unplanned.count, drafts: n.drafts.reduce((sum, one) => sum + one.count, 0) } };
  const now = JSON.stringify(data);
  if (now === drawn) return;
  drawn = now;
  placed.notes = [];
  placed.actions = [];
  places.emit("onecrm_home.shown", data, {
    note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
    action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
  });
}
</script>
