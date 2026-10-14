<template>
  <!-- OneBook's Home (one_book/page/books): how the money is doing, what
       needs somebody today, and everything in OneBook with what it is for
       (one_book/home.py, one_book/story.py). Reports and Setup open their
       part of it. Modelled on Frappe Books' Dashboard: the figures that
       matter, then cash flow, profit and the largest expenses, then where
       the receivables and payables stand; laid out as OneInventory's Home. -->
  <Page wide>
    <Loading v-if="!said" />
    <template v-else>
      <!-- The headline figures, each with its months as a sparkline. -->
      <div v-if="cards.length" ref="cardsRoot" class="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <NumberCard v-for="card in cards" :key="card.key" v-bind="card.props" class="cursor-pointer" role="link" @click="go(card.route)" />
      </div>
      <ViewTabs v-model="shown" :views="views" class="mt-5" />

      <!-- Overview: what needs somebody, then the story of the money. -->
      <template v-if="shown === 'overview'">
        <Loading v-if="!story" />
        <BooksStory v-else :story="story" :needs="chips" @today="shown = 'today'" />
      </template>

      <!-- Today: what needs somebody, kind by kind, the empty kinds left out. -->
      <template v-else-if="shown === 'today'">
        <p v-if="!parts.length" class="py-10 text-center text-base text-ink-gray-5">{{ __("Nothing needs you") }}</p>
        <Section v-for="part in parts" :key="part.key" :title="part.title" :icon="part.icon" :aside="part.count" :action="part.action">
          <Rows :rows="part.rows" />
          <button v-if="part.more" type="button" class="mt-2 text-sm text-ink-gray-5 hover:underline" @click="go(part.more.route)">{{ part.more.label }}</button>
        </Section>
      </template>

      <!-- Everything, or one part of it, each with what it is for. -->
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
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { TextInput } from "frappe-ui";
import { NumberCard, useChartTokens } from "frappe-ui/charts";

import { Loading, Page, Rows, Section, ViewTabs, __, call, count, date, followList, go, money, newDoc, setQuery } from "../kit";
import BooksStory from "./BooksStory.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
  onActions: Function,
});

const said = ref(null);
// Overview, Today, everything, or one part of it: /desk/books/reports opens Reports.
const shown = ref(props.route[0] || props.query.view || "overview");
const search = ref("");
// The story is read beside what needs somebody, so Today never waits on it.
const story = ref(null);

async function load() {
  call("onedesk.one_book.story.read").then((got) => (story.value = got));
  said.value = await call("onedesk.one_book.home.read");
  report();
}
load();

// What needs somebody changes with every invoice, payment and bank line.
let timer = null;
const soon = () => {
  clearTimeout(timer);
  timer = setTimeout(load, 800);
};
const stop = ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry", "Bank Transaction", "GL Entry", "Account"].map((one) => followList(one, soon));
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
  return n.overdue.count + n.bills.count + n.bank.count + n.drafts.reduce((sum, one) => sum + one.count, 0);
});

// The headline figures: what the bank and cash accounts hold, what customers
// owe and how much of it is late, what is owed to suppliers and what falls
// due this week, and this month's profit. Cash and profit are set against
// last month; what is owed is drawn over what was invoiced each month, which
// is not what it counts, so it is not (`alone`).
const CARDS = () => [
  { key: "cash", title: __("Cash"), type: "area", hue: 0, route: "/desk/query-report/Cash Flow" },
  { key: "receivable", title: __("Accounts Receivable"), type: "bar", hue: 2, alone: true, route: "/desk/query-report/Accounts Receivable" },
  { key: "overdue", title: __("Overdue"), route: "/desk/sales-invoice?status=Overdue" },
  { key: "payable", title: __("Accounts Payable"), type: "bar", hue: 6, alone: true, route: "/desk/query-report/Accounts Payable" },
  { key: "due_this_week", title: __("Due This Week"), route: '/desk/purchase-invoice?status=["in",["Unpaid","Overdue","Partly Paid"]]' },
  { key: "profit", title: __("Profit This Month"), type: "bar", hue: 4, route: "/desk/query-report/Profit and Loss Statement" },
];
// The cards' colours, as frappe-ui reads them for this island and its theme.
const cardsRoot = ref();
const { tokens } = useChartTokens(cardsRoot);
const change = (series) => {
  const [before, now] = (series || []).slice(-2);
  return before ? Math.round(((now - before) / Math.abs(before)) * 100) : null;
};
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
        format: (value) => money(value, story.value.currency, 0),
        ...(one.alone || change(got[one.key].series) === null ? {} : { delta: change(got[one.key].series), deltaSuffix: "%", deltaCaption: __("vs last month") }),
        ...(got[one.key].series ? { sparkline: { data: got[one.key].series, type: one.type, color: hues[one.hue] || undefined } } : {}),
      },
    }));
});

// What needs somebody, one button each, leading to Today.
const chips = computed(() => {
  const n = said.value?.needs;
  if (!n) return [];
  const drafts = n.drafts.reduce((sum, d) => sum + d.count, 0);
  return [
    n.overdue.count && { key: "overdue", tone: "late", icon: "lucide-file-warning", label: n.overdue.count === 1 ? __("1 Overdue Sales Invoice") : __("{0} Overdue Sales Invoices", [n.overdue.count]) },
    n.bills.count && { key: "bills", tone: "soon", icon: "lucide-receipt", label: n.bills.count === 1 ? __("1 Purchase Invoice Due") : __("{0} Purchase Invoices Due", [n.bills.count]) },
    n.bank.count && { key: "bank", tone: "soon", icon: "lucide-landmark", label: n.bank.count === 1 ? __("1 Unreconciled Bank Transaction") : __("{0} Unreconciled Bank Transactions", [n.bank.count]) },
    drafts && { key: "drafts", tone: "left", icon: "lucide-file-pen-line", label: drafts === 1 ? __("1 Draft Left") : __("{0} Drafts Left", [drafts]) },
  ].filter(Boolean);
});

const ICONS = { DocType: "lucide-list", Report: "lucide-chart-column", Page: "lucide-layout-panel-top", Masters: "lucide-tags" };

function slug(doctype) {
  return doctype.toLowerCase().replace(/ /g, "-");
}

function route(one) {
  if (one.kind === "Report") return `/desk/query-report/${encodeURIComponent(one.target)}`;
  if (one.kind === "Page") return `/desk/${one.target}`;
  if (one.kind === "Masters") return `/desk/masters?type=${encodeURIComponent(one.target)}`;
  const filters = Object.entries(one.filters || {}).map(([key, value]) => `${key}=${encodeURIComponent(typeof value === "object" ? JSON.stringify(value) : value)}`);
  return `/desk/${slug(one.target)}${filters.length ? `?${filters.join("&")}` : ""}`;
}

const groups = computed(() => {
  const words = search.value.trim().toLowerCase();
  const matches = (one) => !words || `${one.label} ${one.about}`.toLowerCase().includes(words);
  // Reports and Setup set out by what each part is about, a section to a
  // topic, as ERPNext's Financial Reports sidebar does.
  const sections = said.value.sections?.[shown.value];
  if (sections)
    return sections
      .map((topic) => ({ ...topic, rows: said.value.everything.filter((one) => one.group === shown.value && one.topic === topic.key && matches(one)) }))
      .filter((topic) => topic.rows.length);
  return said.value.groups
    .map((group) => ({ ...group, rows: said.value.everything.filter((one) => one.group === group.key && matches(one)) }))
    .filter((group) => group.rows.length);
});

const owed = (one) => money(one.outstanding, one.currency);
const late = (days) => (days === 1 ? __("1 day late") : __("{0} days late", [days]));

// Each kind of thing that needs somebody, as rows, and where the rest are.
const parts = computed(() => {
  const n = said.value.needs;
  const more = (kept, label, where) => (kept.count > kept.rows.length ? { label: __("{0} more", [kept.count - kept.rows.length]) + " · " + label, route: where } : null);
  const out = [];
  if (n.overdue.count)
    out.push({
      key: "overdue",
      title: __("Overdue"),
      icon: "lucide-file-warning",
      count: n.overdue.count,
      rows: n.overdue.rows.map((one) => ({
        key: one.name,
        label: one.party,
        sub: one.name,
        dot: "red",
        value: owed(one),
        under: late(one.late),
        route: `/desk/sales-invoice/${encodeURIComponent(one.name)}`,
      })),
      more: more(n.overdue, __("Sales Invoice"), "/desk/sales-invoice?status=Overdue"),
    });
  if (n.bills.count)
    out.push({
      key: "bills",
      title: __("Purchase Invoices Due"),
      icon: "lucide-receipt",
      count: n.bills.count,
      rows: n.bills.rows.map((one) => ({
        key: one.name,
        label: one.party,
        sub: one.name,
        dot: one.late > 0 ? "red" : "amber",
        value: owed(one),
        under: one.late > 0 ? late(one.late) : one.late === 0 ? __("Due today") : __("Due {0}", [date(one.due_date)]),
        route: `/desk/purchase-invoice/${encodeURIComponent(one.name)}`,
      })),
      more: more(n.bills, __("Purchase Invoice"), '/desk/purchase-invoice?status=["in",["Unpaid","Overdue","Partly Paid"]]'),
    });
  if (n.bank.count)
    out.push({
      key: "bank",
      title: __("Unreconciled Bank Transactions"),
      icon: "lucide-landmark",
      count: n.bank.count,
      action: { text: true, label: __("Bank Reconciliation Tool"), icon: "lucide-git-compare-arrows", onClick: () => go("/desk/bank-reconciliation-tool") },
      rows: n.bank.rows.map((one) => ({
        key: one.bank_account || "",
        label: one.bank_account || __("No Bank Account"),
        dot: "amber",
        value: one.lines === 1 ? __("1 transaction") : __("{0} transactions", [count(one.lines)]),
        under: money(one.amount, story.value?.currency),
        route: `/desk/bank-transaction?status=Unreconciled${one.bank_account ? `&bank_account=${encodeURIComponent(one.bank_account)}` : ""}`,
      })),
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
  props.onTitle?.({ title: __("OneBook") });
  const can = (doctype) => s.everything.some((one) => one.kind === "DocType" && one.target === doctype);
  props.onActions?.(
    [
      can("Sales Invoice") && { label: __("New Sales Invoice"), primary: true, onClick: () => newDoc("Sales Invoice") },
      can("Purchase Invoice") && { label: __("New Purchase Invoice"), onClick: () => newDoc("Purchase Invoice") },
      can("Payment Entry") && { label: __("New Payment Entry"), onClick: () => newDoc("Payment Entry") },
      can("Journal Entry") && { label: __("New Journal Entry"), onClick: () => newDoc("Journal Entry") },
    ].filter(Boolean)
  );
}
</script>
