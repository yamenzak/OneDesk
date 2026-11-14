<template>
  <div class="mx-auto flex min-h-dvh w-full max-w-lg flex-col px-4 pb-4 pt-4 sm:px-6 sm:pt-10">
    <div class="flex h-8 items-center gap-3">
      <Button v-if="backable" variant="ghost" icon="lucide-chevron-left" :aria-label="__('Back')" @click="back" />
      <Progress class="flex-1" size="sm" :value="progress" />
      <Ask v-if="offer && current" :step="current" />
    </div>
    <Empty v-if="failed" :title="__('Not found')" :line="failed" />
    <Loading v-else-if="!offer || !current" />
    <template v-else>
      <div class="mt-8">
        <p v-if="appStep" class="mb-1 text-sm text-ink-gray-6">{{ appStep.app_name }}</p>
        <h1 class="text-2xl font-semibold text-ink-gray-9">{{ heading[0] }}</h1>
        <p v-if="heading[1]" class="mt-2 text-p-base text-ink-gray-6">{{ heading[1] }}</p>
      </div>
      <div class="mt-6 flex-1">
        <component :is="part" :key="current" ref="shown" :step="appStep" />
      </div>
      <div v-if="!shown?.own" class="sticky bottom-0 mt-6 flex flex-col gap-2 bg-surface-base pb-2 pt-3">
        <ErrorMessage :message="error" />
        <Button variant="solid" size="lg" :label="__('Continue')" :loading="busy" :disabled="!shown?.ready" @click="next" />
        <Button v-if="SKIPPED.includes(kind)" variant="ghost" size="lg" :label="__('Set Up Later')" :disabled="busy" @click="skip" />
        <p v-if="current === 'you'" class="text-center text-p-sm text-ink-gray-5" v-html="agreeing" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Button, ErrorMessage, Progress } from "frappe-ui";

import Empty from "../parts/Empty.vue";
import Loading from "../parts/Loading.vue";
import AppStep from "../start/AppStep.vue";
import Ask from "../start/Ask.vue";
import Apps from "../start/Apps.vue";
import Companies from "../start/Companies.vue";
import Company from "../start/Company.vue";
import Field from "../start/Field.vue";
import Language from "../start/Language.vue";
import Payment from "../start/Payment.vue";
import People from "../start/People.vue";
import Plan from "../start/Plan.vue";
import Region from "../start/Region.vue";
import Week from "../start/Week.vue";
import You from "../start/You.vue";
import { after, before, finish, held, left, load, note, offer, save, steps } from "../start/wizard";
import { __ } from "../words";

const PARTS = { you: You, company: Company, language: Language, field: Field, companies: Companies, apps: Apps, plan: Plan, region: Region, payment: Payment, week: Week, steps: AppStep, people: People };
const SKIPPED = ["companies", "week", "steps", "people"];

const route = useRoute();
const at = ref(-1);
const shown = ref(null);
const busy = ref(false);
const error = ref("");
const failed = ref("");

const current = computed(() => steps.value[at.value]);
const kind = computed(() => (current.value || "").split(":")[0]);
const part = computed(() => PARTS[kind.value]);
const appStep = computed(() => held.steps.find((one) => one.id === current.value) || null);
const progress = computed(() => (steps.value.length ? Math.round((100 * Math.max(at.value, 0)) / steps.value.length) : 0));
const backable = computed(() => at.value > 0 && !(held.paid && at.value <= before.value.length));

const heading = computed(() => {
  if (appStep.value) return [appStep.value.title, appStep.value.about];
  return {
    you: [__("Your Name"), __("You will be the workspace's first administrator.")],
    company: [__("Your Company"), __("The workspace takes its name, and its address starts with it.")],
    language: [__("Language and Currency"), __("Used for the workspace, its books and its dates.")],
    field: [__("What the Company Does"), __("The apps that suit it are turned on. You can change them next.")],
    companies: [__("More Companies"), __("Add each other company the workspace keeps books for.")],
    apps: [__("Apps"), __("Turn on what the company will use. Any app can be turned on later.")],
    plan: [__("Plan"), ""],
    region: [__("Where Data Is Kept"), ""],
    payment: [__("Payment"), __("The workspace is built once the payment is accepted.")],
    week: [__("Working Week"), __("Used for attendance, leave and the calendar.")],
    people: [__("People"), __("Each person gets an invitation by email once the workspace is ready.")],
  }[kind.value] || ["", ""];
});

const link = (href, text) => `<a class="underline" href="${href}" target="_blank" rel="noopener">${text}</a>`;
const agreeing = __("By continuing you agree to the {0} and the {1}.", [link("/legal/terms", __("Terms of Service")), link("/legal/privacy", __("Privacy Policy"))]);

watch(current, (step, was) => {
  if (step) note(step, "Reached");
  error.value = "";
  if (was !== undefined) window.scrollTo({ top: 0 });
});

function opening() {
  if (route.query.paid || held.paid || after.value.includes(held.step)) {
    if (route.query.paid) note("payment", "Finished");
    const done = after.value.indexOf(held.step);
    return before.value.length + Math.min(done + 1, after.value.length - 1);
  }
  const done = before.value.indexOf(held.step);
  return held.request ? Math.min(done + 1, before.value.indexOf("payment")) : 0;
}

async function next() {
  busy.value = true;
  error.value = "";
  try {
    await save(current.value, shown.value.said(), [{ step: current.value, event: "Finished" }]);
    await onward();
  } catch (refused) {
    error.value = refused?.messages?.[0] || __("That did not work. Try again in a moment.");
  } finally {
    busy.value = false;
  }
}

async function skip() {
  note(current.value, "Skipped");
  await onward();
}

async function onward() {
  if (at.value < steps.value.length - 1) return (at.value += 1);
  await finish([]);
  window.location.href = `/welcome?request=${encodeURIComponent(held.request)}&key=${encodeURIComponent(held.key)}`;
}

const back = () => (at.value -= 1);

const leaving = () => current.value && current.value !== "payment" && left(current.value);

onMounted(async () => {
  try {
    await load(route.query);
    at.value = opening();
  } catch (refused) {
    failed.value = refused?.messages?.[0] || __("Signups are not taken here.");
  }
  window.addEventListener("pagehide", leaving);
});

onBeforeUnmount(() => window.removeEventListener("pagehide", leaving));
</script>
