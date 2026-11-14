<template>
  <div class="space-y-3 text-sm text-ink-gray-8">
    <div v-if="matter" class="text-ink-gray-7">
      <span>{{ matterSaid[0] }}</span>
      <a v-if="matter.document?.route" :href="matter.document.route" class="underline">{{ matter.title }}</a>
      <span v-else>{{ matter.title }}</span>
      <span>{{ matterSaid[1] }}</span>
      <Badge v-if="matter.change && !matter.copy" :label="matter.change" theme="gray" size="sm" class="ms-1" />
    </div>
    <dl v-if="facts.length" class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
      <template v-for="fact in facts" :key="fact.label">
        <dt class="text-ink-gray-5">{{ fact.label }}</dt>
        <dd>{{ factValue(fact) }}</dd>
      </template>
    </dl>
    <div v-for="list in lists" :key="list.title">
      <div class="mb-1 text-xs font-medium text-ink-gray-5">{{ list.title }}</div>
      <ul class="space-y-0.5">
        <li v-for="(row, at) in list.rows" :key="at">
          <template v-for="(bit, i) in row" :key="i">
            <span v-if="i" class="text-ink-gray-4"> · </span>
            <a v-if="bit.href" :href="bit.href" class="underline">{{ bit.text }}</a>
            <span v-else :class="{ 'text-ink-gray-5': bit.quiet, 'font-medium': bit.strong }">{{ bit.text }}</span>
          </template>
        </li>
      </ul>
    </div>
    <details v-if="said.dropped?.length">
      <summary class="cursor-pointer text-ink-gray-5">{{ __("Not in the document ({0})", [said.dropped.length]) }}</summary>
      <ul class="mt-1 space-y-0.5">
        <li v-for="(line, at) in said.dropped" :key="at">{{ line }}</li>
      </ul>
    </details>
  </div>
</template>

<script setup>
// What OneAI read from a document: its facts, who and when, what it asks for,
// its parts and attachments (public/js/one_ai/intake.js drew this for the desk).
import { computed } from "vue";
import { Badge } from "frappe-ui";

import { __, date, money, recordRoute } from "../kit";
const props = defineProps({ said: { type: Object, required: true } });

const matter = computed(() => props.said.matter || null);
// The words around the title, in the reader's language, with the title a link.
const matterSaid = computed(() => (matter.value?.copy ? __("A copy of {0}") : __("About {0}")).split("{0}"));
const facts = computed(() => props.said.facts || []);

function factValue(fact) {
  if (fact.field === "gross") return money(fact.value, fact.currency);
  if (["issued_on", "valid_until"].includes(fact.field)) return date(fact.value);
  if (fact.field === "iban") return String(fact.value).replace(/(.{4})/g, "$1 ").trim();
  return fact.value;
}

const lists = computed(() => {
  const said = props.said;
  const party = (one) => [
    { text: one.role, quiet: true },
    { text: one.name || "" },
    one.record
      ? { text: `${__(one.record[0])} ${one.record[1]}`, href: recordRoute(one.record[0], one.record[1]) }
      : { text: one.ours ? (one.ours === "Company" ? __("us") : __("a colleague")) : __("not known yet"), quiet: true },
  ];
  return [
    { title: __("Who"), rows: (said.parties || []).map(party) },
    {
      title: __("When"),
      rows: (said.dates || []).map((one) => [{ text: `${one.what} ${date(one.date)}` }, one.about && { text: one.about }].filter(Boolean)),
    },
    {
      title: __("Asks"),
      rows: (said.asks || []).map((one) =>
        [{ text: one.what, strong: true }, one.detail && { text: one.detail }, one.by && { text: __("by {0}", [date(one.by)]) }].filter(Boolean)
      ),
    },
    {
      title: __("Documents"),
      rows: (said.parts || []).map((one) => [{ text: one.part || "", quiet: true }, { text: __(one.kind || "") }, { text: one.title || "" }]),
    },
    {
      title: __("Attachments"),
      rows: (said.attachments || []).map((one) => [{ text: one.file }, { text: __(one.kind || one.state || "") }, one.title && { text: one.title }].filter(Boolean)),
    },
  ].filter((list) => list.rows.length);
});
</script>
