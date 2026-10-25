<template>
  <div v-if="said" class="rounded-4 border border-outline-gray-1 p-3 text-sm">
    <div class="flex flex-wrap items-center gap-1.5 text-ink-gray-6">
      <img :src="oneaiMark" alt="" class="size-4" />
      <span>{{ __("Read by OneAI") }}</span>
      <Badge v-if="junk" :label="__(said.verdict)" :theme="said.verdict === 'Phishing' ? 'red' : 'gray'" size="sm" />
      <Badge v-if="!junk && said.kind" :label="__(said.kind)" theme="blue" size="sm" />
      <Badge v-if="!junk && said.unsure" :label="__('Unsure')" theme="amber" size="sm" />
    </div>
    <template v-if="!junk">
      <div v-if="said.title" class="mt-2 font-medium text-ink-gray-9">{{ said.title }}</div>
      <div v-if="said.summary" class="mt-1 text-ink-gray-7">{{ said.summary }}</div>
      <dl v-if="said.quick?.length" class="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <template v-for="one in said.quick" :key="one.label">
          <dt class="text-ink-gray-5">{{ one.label }}</dt>
          <dd>{{ quickValue(one) }}</dd>
        </template>
      </dl>
      <a v-if="acts.length" :href="statusRoute" class="mt-2 flex flex-wrap items-center gap-1.5 text-ink-gray-7 hover:underline">
        <Badge v-if="waits" :label="__('{0} to decide', [waits])" theme="amber" size="sm" />
        {{ done === 1 ? __("OneAI did 1 thing with it") : __("OneAI did {0} things with it", [done]) }} →
      </a>
      <div class="mt-2 flex flex-wrap gap-1.5">
        <Button v-if="said.pay" size="sm" :label="said.pay.warn ? __('Do Not Pay Yet') : __('Pay')" :variant="open === 'pay' ? 'solid' : 'subtle'" @click="fold('pay')" />
        <Button size="sm" :label="__('Details')" :variant="open === 'details' ? 'solid' : 'subtle'" @click="fold('details')" />
      </div>
      <IntakePay v-if="open === 'pay'" :pay="said.pay" class="mt-3" />
      <IntakeFacts v-if="open === 'details'" :said="said" class="mt-3" />
      <IntakeExplain :said="said" class="mt-3" />
    </template>
  </div>
</template>

<script setup>
// What OneAI read from a file or a message, beside it in OneCloud's preview
// and under it in OneMail: what it is, the few facts that matter, what OneAI
// did with it (in Documents), how to pay it and its plain-words
// explanation.
import { computed, ref, watch } from "vue";
import { Badge, Button } from "frappe-ui";

import { __, call, date, intakeOn, money, oneaiMark } from "../kit";
import IntakeExplain from "./IntakeExplain.vue";
import IntakeFacts from "./IntakeFacts.vue";
import IntakePay from "./IntakePay.vue";

const props = defineProps({ file: String, message: String });

const JUNK = ["Spam", "Advertising", "Newsletter", "Notification", "Phishing"];
const said = ref(null);
const open = ref(null);

async function load() {
  said.value = null;
  open.value = null;
  if (!intakeOn() || !(props.file || props.message)) return;
  try {
    const got = props.file
      ? await call("onedesk.one_ai.reading.panel.for_file", { name: props.file })
      : await call("onedesk.one_ai.reading.panel.for_message", { name: props.message });
    if (got && (got.read_by_ai || got.verdict)) said.value = got;
  } catch (e) {
    said.value = null;
  }
}
watch(() => [props.file, props.message], load, { immediate: true });

const junk = computed(() => !said.value.read_by_ai || (JUNK.includes(said.value.verdict) && !said.value.kind));
const acts = computed(() => said.value.actions || []);
const waits = computed(() => acts.value.filter((one) => one.level === "Proposed" || (one.level === "Done" && one.audit === "Wrong")).length);
const done = computed(() => acts.value.filter((one) => one.level === "Done").length);
const statusRoute = computed(() => `/desk/intake?box=${waits.value ? "waiting" : "done"}&reading=${encodeURIComponent(said.value.name)}`);

const quickValue = (one) => (one.type === "currency" ? money(one.value, one.currency) : one.type === "date" ? date(one.value) : String(one.value));
const fold = (key) => (open.value = open.value === key ? null : key);
</script>
