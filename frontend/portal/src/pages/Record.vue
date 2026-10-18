<template>
  <Head :title="doc?.name || name" :crumbs="token ? [] : [{ label: tab, route: `/${kind}` }]" :badge="doc">
    <template #actions>
      <Button
        v-for="one in quiet"
        :key="one.href"
        :label="phone && one.icon ? undefined : one.label"
        :aria-label="one.label"
        :icon="phone && one.icon ? `lucide-${one.icon}` : undefined"
        :icon-left="!phone && one.icon ? `lucide-${one.icon}` : undefined"
        :href="one.href"
      />
    </template>
  </Head>
  <div class="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">
    <Loading v-if="!doc && !failed" />
    <Empty v-else-if="failed" :title="__('No access')" :line="__('This is not one of yours, or it was taken away.')" />
    <div v-else class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div class="contents lg:flex lg:min-w-0 lg:flex-col lg:gap-5">
        <Card v-if="doc.steps.length"><Steps :steps="doc.steps" /></Card>

        <Card :title="__('Items')" :count="doc.items.length" flush>
          <ul>
            <li v-for="(item, i) in doc.items" :key="i" class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-3 last:border-b-0">
              <Thumb :image="item.image" />
              <div class="min-w-0 flex-1">
                <p class="truncate text-base text-ink-gray-9">{{ item.item }}</p>
                <p v-if="item.about" class="truncate text-sm text-ink-gray-5">{{ item.about }}</p>
                <p class="text-sm tabular-nums text-ink-gray-6">
                  <bdi>{{ item.qty }} {{ item.uom }}</bdi> ×
                  <template v-if="item.discount"><bdi>{{ item.list_rate }}</bdi> <bdi class="text-ink-green-6">− {{ item.discount }}</bdi></template>
                  <bdi v-else>{{ item.rate }}</bdi>
                </p>
              </div>
              <p class="shrink-0 text-base font-medium tabular-nums text-ink-gray-9">{{ item.amount }}</p>
            </li>
          </ul>
          <template #foot>
            <dl class="ms-auto grid max-w-xs grid-cols-[1fr_auto] gap-x-6 gap-y-1.5">
              <template v-for="one in doc.totals" :key="one.label">
                <dt :class="one.strong ? 'text-base font-medium text-ink-gray-9' : 'text-base text-ink-gray-6'">{{ one.label }}</dt>
                <dd :class="['text-end tabular-nums', one.strong ? 'text-base font-semibold text-ink-gray-9' : 'text-base text-ink-gray-7']">{{ one.value }}</dd>
              </template>
            </dl>
          </template>
        </Card>

        <Card v-if="doc.terms" :title="doc.terms_label">
          <div class="prose prose-sm max-w-none text-ink-gray-7" v-html="doc.terms" />
        </Card>
      </div>

      <aside class="contents lg:flex lg:flex-col lg:gap-5">
        <Card class="order-first lg:order-none">
          <p class="text-sm text-ink-gray-6">{{ doc.summary.label }}</p>
          <p class="mt-1 text-3xl font-semibold tabular-nums text-ink-gray-9">{{ doc.summary.value }}</p>
          <p v-if="doc.summary.line" :class="['mt-1 text-sm', doc.summary.late ? 'text-ink-red-6' : 'text-ink-gray-6']">{{ doc.summary.line }}</p>
          <Button v-for="one in solid" :key="one.href" class="mt-4 w-full" variant="solid" size="md" :label="one.label" :href="one.href" />
          <p v-if="answered" class="mt-3 text-sm text-ink-gray-6">{{ __("Answered by {0}, {1}.", [answered.by, answered.on]) }}</p>
          <div v-if="doc.answer" class="mt-4 flex flex-col gap-2">
            <Button variant="solid" size="md" :label="__('Accept Quotation')" icon-left="lucide-check" @click="accepting = true" />
            <Button size="md" :label="__('Decline')" @click="declining = true" />
          </div>
        </Card>

        <Card :title="__('Details')">
          <dl class="flex flex-col gap-3">
            <div v-for="one in doc.facts" :key="one.label" class="flex justify-between gap-4">
              <dt class="shrink-0 text-sm text-ink-gray-5">{{ one.label }}</dt>
              <dd :class="['text-end text-sm text-ink-gray-8', one.lines && 'whitespace-pre-line']">{{ one.value }}</dd>
            </div>
          </dl>
        </Card>

        <Card v-if="doc.related.length" :title="__('Linked')" flush>
          <LinkRow
            v-for="one in doc.related"
            :key="one.to"
            :to="`/${one.to}`"
            :name="one.name"
            :line="`${one.kind} · ${one.figure}`"
            :status="one.status"
            :tone="one.tone"
          />
        </Card>

        <Card v-if="doc.files.length" :title="__('Files')" flush>
          <a
            v-for="one in doc.files"
            :key="one.url"
            :href="one.url"
            target="_blank"
            rel="noopener"
            class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-2.5 text-sm text-ink-gray-8 last:border-b-0 hover:bg-surface-gray-1"
          >
            <span class="lucide-paperclip size-4 text-ink-gray-5" aria-hidden="true" />
            <span class="truncate">{{ one.name }}</span>
          </a>
        </Card>
      </aside>
    </div>
    <Dialog v-model="accepting" :title="__('Accept Quotation')">
      <template #default>
        <div class="flex flex-col gap-4">
          <p class="text-p-base text-ink-gray-7">{{ __("We'll prepare your order for {0} and confirm it with you.", [doc?.summary.value]) }}</p>
          <FormControl v-model="wanted" type="date" :label="__('Needed by')" :min="today" required />
          <FormControl v-model="reference" type="text" :label="__('Your reference')" :placeholder="__('Your purchase order number, if you have one')" />
          <FormControl v-if="token" v-model="by" type="text" :label="__('Your name')" required />
        </div>
      </template>
      <template #actions>
        <Button class="w-full" variant="solid" :label="__('Accept Quotation')" :loading="busy" :disabled="!wanted || (token && !by.trim())" @click="accept" />
      </template>
    </Dialog>
    <Dialog v-model="declining" :title="__('Decline Quotation')">
      <template #default>
        <div class="flex flex-col gap-4">
          <Textarea v-model="reason" :label="__('Why? (optional)')" :placeholder="__('The price, the timing, another supplier…')" :rows="3" />
          <FormControl v-if="token" v-model="by" type="text" :label="__('Your name')" required />
        </div>
      </template>
      <template #actions>
        <Button class="w-full" theme="red" variant="solid" :label="__('Decline Quotation')" :loading="busy" :disabled="token && !by.trim()" @click="decline" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Button, Dialog, FormControl, Textarea, toast } from "frappe-ui";

import { call } from "../call";
import Card from "../parts/Card.vue";
import Empty from "../parts/Empty.vue";
import Head from "../parts/Head.vue";
import LinkRow from "../parts/LinkRow.vue";
import Loading from "../parts/Loading.vue";
import Steps from "../parts/Steps.vue";
import Thumb from "../parts/Thumb.vue";
import { phone } from "../phone";
import { __, boot } from "../words";

const props = defineProps({
  kind: { type: String, default: "" },
  name: { type: String, default: "" },
  token: { type: String, default: "" },
  link: { type: Object, default: null },
});

const tab = computed(() => boot().tabs?.find((one) => one.path === props.kind)?.title || "");
const doc = ref(props.link?.page || null);
const answered = ref(props.link?.answered || null);
const failed = ref(false);
const solid = computed(() => (doc.value?.actions || []).filter((one) => one.solid));
const quiet = computed(() => (doc.value?.actions || []).filter((one) => !one.solid));

async function load() {
  failed.value = false;
  try {
    if (props.token) {
      const said = await call("onedesk.one.portal_share.link_view", { token: props.token });
      doc.value = said.page;
      answered.value = said.answered;
    } else {
      doc.value = await call("record", { kind: props.kind, name: props.name });
    }
  } catch {
    failed.value = true;
  }
}

watch(
  () => [props.kind, props.name],
  () => {
    if (props.token) return;
    doc.value = null;
    load();
  },
  { immediate: true },
);

const accepting = ref(false);
const declining = ref(false);
const busy = ref(false);
const today = new Date().toISOString().slice(0, 10);
const wanted = ref("");
const reference = ref("");
const reason = ref("");
const by = ref("");

async function answer(method, args, said) {
  busy.value = true;
  try {
    if (props.token) await call(`onedesk.one.portal_share.link_${method}`, { token: props.token, by: by.value, ...args });
    else await call(`${method}_quote`, { kind: props.kind, name: props.name, ...args });
    toast.success(said);
    accepting.value = declining.value = false;
    await load();
  } catch (error) {
    toast.error(error?.messages?.[0] || __("Something went wrong. Try again in a moment."));
  } finally {
    busy.value = false;
  }
}
const accept = () => answer("accept", { wanted: wanted.value, reference: reference.value }, __("Accepted. We'll confirm your order."));
const decline = () => answer("decline", { reason: reason.value }, __("Quotation declined"));
</script>
