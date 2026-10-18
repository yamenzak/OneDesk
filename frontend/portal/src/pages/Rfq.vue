<template>
  <Head :title="doc?.name || name" :crumbs="token ? [] : [{ label: tab, route: '/rfq' }]" :badge="doc" />
  <div class="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">
    <Loading v-if="!doc && !failed" />
    <Empty v-else-if="failed" :title="__('No access')" :line="__('This request was not sent to you, or it is closed.')" />
    <div v-else class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div class="contents lg:flex lg:min-w-0 lg:flex-col lg:gap-5">
        <Card v-if="doc.message" :title="__('From the buyer')" icon="lucide-message-square">
          <div class="prose prose-sm max-w-none text-ink-gray-7" v-html="doc.message" />
        </Card>
        <Card :title="__('Items')" :count="doc.rows.length" flush>
      <List :columns="phone || !open ? ['minmax(0,1fr)'] : ['minmax(0,1fr)', '6rem', '7rem', '6rem', '7rem', '8rem']" class="list-row-px-4">
        <ListHeader v-if="!phone && open">
          <ListHeaderCell>{{ __("Item") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Quantity") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Rate") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Discount %") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Tax") }}</ListHeaderCell>
          <ListHeaderCell class="justify-end">{{ __("Amount") }}</ListHeaderCell>
        </ListHeader>
        <ListRows :items="doc.rows" row-key="name" v-slot="{ item }">
          <ListRow>
            <ListCell class="flex-col !items-start gap-0.5 py-2">
              <span class="text-base text-ink-gray-8">{{ item.item }}</span>
              <span v-if="item.about" class="text-sm text-ink-gray-5">{{ item.about }}</span>
              <span class="text-sm text-ink-gray-5">
                {{ __("{0} {1} asked for", [item.qty_said, item.uom]) }}<template v-if="item.needed_by"> · {{ __("by {0}", [item.needed_by]) }}</template>
              </span>
              <template v-if="phone && open">
                <div class="mt-2 grid w-full grid-cols-3 gap-x-2 gap-y-1">
                  <span class="text-xs text-ink-gray-5">{{ __("Quantity") }}</span>
                  <span class="text-xs text-ink-gray-5">{{ __("Rate") }}</span>
                  <span class="text-xs text-ink-gray-5">{{ __("Discount %") }}</span>
                  <TextInput v-model="answer[item.name].qty" type="number" min="0" :placeholder="__('Quantity')" :aria-label="__('Quantity')" />
                  <TextInput v-model="answer[item.name].rate" type="number" min="0" :placeholder="__('Rate')" :aria-label="__('Rate')" />
                  <TextInput v-model="answer[item.name].discount" type="number" min="0" max="100"  placeholder="0" :aria-label="__('Discount %')" />
                </div>
                <span v-if="said(item.name)" class="mt-1 text-sm tabular-nums text-ink-gray-6">
                  {{ said(item.name).net }}<template v-if="said(item.name).rate"> · {{ __("Tax {0}", [said(item.name).rate]) }} {{ said(item.name).tax }}</template>
                </span>
              </template>
            </ListCell>
            <template v-if="!phone && open">
              <ListCell class="justify-end">
                <TextInput v-model="answer[item.name].qty" type="number" min="0" class="w-20 text-end" :aria-label="__('Quantity')" />
              </ListCell>
              <ListCell class="justify-end">
                <TextInput v-model="answer[item.name].rate" type="number" min="0" class="w-24 text-end" :aria-label="__('Rate')" />
              </ListCell>
              <ListCell class="justify-end">
                <TextInput v-model="answer[item.name].discount" type="number" min="0" max="100" placeholder="0" class="w-20 text-end" :aria-label="__('Discount %')" />
              </ListCell>
              <ListCell class="flex-col !items-end justify-center gap-0.5 tabular-nums">
                <span class="text-base text-ink-gray-7">{{ said(item.name)?.tax || "" }}</span>
                <span v-if="said(item.name)?.rate" class="text-sm text-ink-gray-5">{{ said(item.name).rate }}</span>
              </ListCell>
              <ListCell class="flex-col !items-end justify-center gap-0.5 tabular-nums">
                <span class="text-base text-ink-gray-8">{{ said(item.name)?.net || money(amount(item.name), doc.money) }}</span>
                <span v-if="said(item.name)?.discount" class="text-sm text-ink-green-6">−{{ said(item.name).discount }}</span>
              </ListCell>
            </template>
          </ListRow>
        </ListRows>
      </List>
          <template v-if="open" #foot>
            <dl class="ms-auto grid max-w-xs grid-cols-[1fr_auto] gap-x-6 gap-y-1.5 text-base">
              <dt class="text-ink-gray-6">{{ __("Net Total") }}</dt>
              <dd class="text-end tabular-nums text-ink-gray-7">{{ preview?.net || money(total, doc.money) }}</dd>
              <template v-for="one in preview?.taxes || []" :key="one.label">
                <dt class="text-ink-gray-6">{{ one.label }}</dt>
                <dd class="text-end tabular-nums text-ink-gray-7">{{ one.value }}</dd>
              </template>
              <dt class="font-medium text-ink-gray-9">{{ __("Total") }}</dt>
              <dd class="text-end font-semibold tabular-nums text-ink-gray-9">{{ grand }}</dd>
            </dl>
          </template>
        </Card>
        <Card v-if="open" :title="__('Notes')">
          <div class="flex flex-col gap-4">
            <Textarea v-model="notes" :placeholder="__('When you can deliver, and anything the buyer should know.')" :rows="3" />
            <FormControl v-if="token" v-model="by" type="text" :label="__('Your name')" required />
          </div>
        </Card>
        <Card v-if="doc.terms" :title="__('Terms')">
          <div class="prose prose-sm max-w-none text-ink-gray-7" v-html="doc.terms" />
        </Card>
      </div>

      <aside class="contents lg:flex lg:flex-col lg:gap-5">
        <Card v-if="open" class="order-first lg:order-none">
          <p class="text-sm text-ink-gray-6">{{ __("Your quote") }}</p>
          <p class="mt-1 text-3xl font-semibold tabular-nums text-ink-gray-9">{{ grand }}</p>
          <p v-if="preview?.taxes?.length" class="text-sm text-ink-gray-6">{{ __("Including {0}", [preview.taxes.map((one) => one.label).join(", ")]) }}</p>
          <p class="mt-1 text-sm text-ink-gray-6">{{ priced ? __("{0} of {1} items priced", [pricedRows, doc.rows.length]) : __("Set a rate for each item you can supply.") }}</p>
          <Button class="mt-4 w-full" variant="solid" size="md" :label="__('Send Quote')" :loading="sending" :disabled="!priced || (token && !by.trim())" @click="send" />
        </Card>
        <Card v-if="doc.quotes.length" :title="__('Your Quotes')" flush>
          <p v-if="answered" class="px-4 pt-3 text-sm text-ink-gray-6">{{ __("Answered by {0}, {1}.", [answered.by, answered.on]) }}</p>
          <LinkRow
            v-for="one in doc.quotes"
            :key="one.name"
            :to="token ? '' : `/supplier-quotations/${one.name}`"
            :name="one.name"
            :line="`${one.date} · ${one.total}`"
            :status="one.status"
            :tone="one.tone"
          />
        </Card>
        <Card :title="__('Details')">
          <dl class="flex flex-col gap-3">
            <div v-for="one in doc.facts" :key="one.label" class="flex justify-between gap-4">
              <dt class="shrink-0 text-sm text-ink-gray-5">{{ one.label }}</dt>
              <dd :class="['text-end text-sm text-ink-gray-8', one.lines && 'whitespace-pre-line']">{{ one.value }}</dd>
            </div>
          </dl>
        </Card>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl, TextInput, Textarea, debounce, toast } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";

import { call } from "../call";
import { money } from "../money";
import Card from "../parts/Card.vue";
import Empty from "../parts/Empty.vue";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import LinkRow from "../parts/LinkRow.vue";
import { phone } from "../phone";
import { __, boot } from "../words";

const props = defineProps({
  name: { type: String, default: "" },
  token: { type: String, default: "" },
  link: { type: Object, default: null },
});
const router = useRouter();

const tab = computed(() => boot().tabs?.find((one) => one.path === "rfq")?.title || "");
const doc = ref(props.link?.page || null);
const answered = ref(props.link?.answered || null);
const failed = ref(false);
const by = ref("");
const answer = reactive({});
const notes = ref("");
const sending = ref(false);

const open = computed(() => Boolean(doc.value && doc.value.open && !doc.value.quoted));
const amount = (row) =>
  (Number(answer[row]?.qty) || 0) * (Number(answer[row]?.rate) || 0) * (1 - Math.min(Number(answer[row]?.discount) || 0, 100) / 100);
const total = computed(() => Object.keys(answer).reduce((sum, row) => sum + amount(row), 0));
const priced = computed(() => total.value > 0);
const pricedRows = computed(() => Object.keys(answer).filter((row) => amount(row) > 0).length);

const preview = ref(null);
const said = (row) => preview.value?.rows?.[row];
const grand = computed(() => preview.value?.total || money(total.value, doc.value.money));
const reckon = debounce(async () => {
  if (!open.value) return;
  try {
    const rows = JSON.stringify(answer);
    preview.value = props.token
      ? await call("onedesk.one.portal_share.link_preview", { token: props.token, rows })
      : await call("quote_preview", { rfq: props.name, rows });
  } catch {
    preview.value = null;
  }
}, 400);
watch(answer, reckon, { deep: true });

async function send() {
  sending.value = true;
  try {
    const rows = JSON.stringify(answer);
    if (props.token) {
      await call("onedesk.one.portal_share.link_send", { token: props.token, rows, notes: notes.value, by: by.value });
      toast.success(__("Quote sent"));
      await load();
      return;
    }
    const quote = await call("send_quote", { rfq: props.name, rows, notes: notes.value });
    toast.success(__("Quote sent"));
    router.push(`/supplier-quotations/${quote}`);
  } catch (error) {
    toast.error(error?.messages?.[0] || __("Couldn't send the quote."));
  } finally {
    sending.value = false;
  }
}

function fill() {
  for (const row of doc.value.rows) answer[row.name] = { qty: row.qty, rate: "", discount: "" };
}

async function load() {
  failed.value = false;
  try {
    if (props.token) {
      const said = await call("onedesk.one.portal_share.link_view", { token: props.token });
      doc.value = said.page;
      answered.value = said.answered;
    } else {
      doc.value = await call("rfq", { name: props.name });
    }
    fill();
  } catch {
    failed.value = true;
  }
}

watch(
  () => props.name,
  () => {
    if (props.token) return;
    doc.value = null;
    load();
  },
  { immediate: true },
);
if (doc.value) fill();
</script>
