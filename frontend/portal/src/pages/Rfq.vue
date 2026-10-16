<template>
  <!-- A quote request sent to the reader's supplier (one/portal.py `rfq`):
       the buyer's message and facts, each row priced in place, notes, and
       Send Quote (`send_quote`). Once answered, the quotes sent instead.
       Modelled on Ariba's supplier quote: price each row in place, send. -->
  <Head :title="name" :crumbs="[{ label: tab, route: '/rfq' }]" :badge="doc">
    <template #actions>
      <Button v-if="open" variant="solid" :label="__('Send Quote')" :loading="sending" :disabled="!priced" @click="send" />
    </template>
  </Head>
  <div class="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6">
    <Loading v-if="!doc && !failed" />
    <Empty v-else-if="failed" :title="__('No access')" :line="__('This request was not sent to you, or it is closed.')" />
    <template v-else>
      <div v-if="doc.message" class="prose prose-sm mb-6 max-w-none text-ink-gray-7" v-html="doc.message" />
      <Facts :facts="doc.facts" />
      <List :columns="phone || !open ? ['minmax(0,1fr)'] : ['minmax(0,1fr)', '7rem', '8rem', '9rem']" class="mt-6 list-row-px-0">
        <ListHeader v-if="!phone">
          <ListHeaderCell>{{ __("Item") }}</ListHeaderCell>
          <template v-if="open">
            <ListHeaderCell class="justify-end">{{ __("Quantity") }}</ListHeaderCell>
            <ListHeaderCell class="justify-end">{{ __("Rate") }}</ListHeaderCell>
            <ListHeaderCell class="justify-end">{{ __("Amount") }}</ListHeaderCell>
          </template>
        </ListHeader>
        <ListRows :items="doc.rows" row-key="name" v-slot="{ item }">
          <ListRow>
            <ListCell class="flex-col !items-start gap-0.5 py-2">
              <span class="text-base text-ink-gray-8">{{ item.item }}</span>
              <span v-if="item.about" class="text-sm text-ink-gray-5">{{ item.about }}</span>
              <span class="text-sm text-ink-gray-5">
                {{ __("{0} {1} asked for", [item.qty_said, item.uom]) }}<template v-if="item.needed_by"> · {{ __("by {0}", [item.needed_by]) }}</template>
              </span>
              <div v-if="phone && open" class="mt-2 grid w-full grid-cols-2 gap-2">
                <TextInput v-model="answer[item.name].qty" type="number" min="0" :placeholder="__('Quantity')" />
                <TextInput v-model="answer[item.name].rate" type="number" min="0" :placeholder="__('Rate')" />
              </div>
            </ListCell>
            <template v-if="!phone && open">
              <ListCell class="justify-end">
                <TextInput v-model="answer[item.name].qty" type="number" min="0" class="w-24 text-end" :aria-label="__('Quantity')" />
              </ListCell>
              <ListCell class="justify-end">
                <TextInput v-model="answer[item.name].rate" type="number" min="0" class="w-28 text-end" :aria-label="__('Rate')" />
              </ListCell>
              <ListCell class="justify-end tabular-nums text-base text-ink-gray-8">{{ money(amount(item.name), doc.money) }}</ListCell>
            </template>
          </ListRow>
        </ListRows>
      </List>
      <template v-if="open">
        <div class="mt-4 flex justify-end gap-6 border-t border-outline-gray-1 pt-4 text-base">
          <span class="font-medium text-ink-gray-9">{{ __("Total") }}</span>
          <span class="font-semibold tabular-nums text-ink-gray-9">{{ money(total, doc.money) }}</span>
        </div>
        <Textarea v-model="notes" class="mt-6" :label="__('Notes')" :placeholder="__('When you can deliver, and anything the buyer should know.')" :rows="3" />
      </template>
      <Section v-if="doc.quotes.length" :title="__('Your Quotes')">
        <Rows :rows="doc.quotes.map((one) => ({ title: one.name, line: one.date, tone: one.tone, status: one.status, figure: one.total, to: `/supplier-quotations/${one.name}` }))" />
      </Section>
      <Section v-if="doc.terms" :title="__('Terms')">
        <div class="prose prose-sm max-w-none text-ink-gray-7" v-html="doc.terms" />
      </Section>
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Button, TextInput, Textarea, toast } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { call } from "../call";
import { money } from "../money";
import Empty from "../parts/Empty.vue";
import Facts from "../parts/Facts.vue";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import Rows from "../parts/Rows.vue";
import Section from "../parts/Section.vue";
import { phone } from "../phone";
import { __, boot } from "../words";

const props = defineProps({ name: { type: String, required: true } });
const router = useRouter();

const tab = computed(() => boot().tabs?.find((one) => one.path === "rfq")?.title || "");
const doc = ref(null);
const failed = ref(false);
const answer = reactive({});
const notes = ref("");
const sending = ref(false);

// A request still to answer: once quoted, it shows the quotes sent instead.
const open = computed(() => Boolean(doc.value && doc.value.open && !doc.value.quoted));
const amount = (row) => (Number(answer[row]?.qty) || 0) * (Number(answer[row]?.rate) || 0);
const total = computed(() => Object.keys(answer).reduce((sum, row) => sum + amount(row), 0));
const priced = computed(() => total.value > 0);

async function send() {
  sending.value = true;
  try {
    const quote = await call("send_quote", { rfq: props.name, rows: JSON.stringify(answer), notes: notes.value });
    toast.success(__("Quote sent"));
    router.push(`/supplier-quotations/${quote}`);
  } catch (error) {
    toast.error(error?.messages?.[0] || __("Couldn't send the quote."));
  } finally {
    sending.value = false;
  }
}

watch(
  () => props.name,
  async () => {
    doc.value = null;
    failed.value = false;
    try {
      doc.value = await call("rfq", { name: props.name });
      for (const row of doc.value.rows) answer[row.name] = { qty: row.qty, rate: "" };
    } catch {
      failed.value = true;
    }
  },
  { immediate: true },
);
</script>
