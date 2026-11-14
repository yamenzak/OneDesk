import { computed, reactive, ref } from "vue";

import { call } from "../call";

const WIZARD = "onedesk.one_admin.wizard";
const KEPT = "one-start";

export const offer = ref(null);
export const held = reactive({ request: null, key: null, status: null, paid: false, plan: null, region: "Global", slug: null, steps: [], seats: 0, apps_on: [], needed_by: {}, step: null });
export const answers = reactive({
  owner: { first_name: "", last_name: "" },
  companies: [{ name: "", country: "" }],
  language: "",
  time_zone: "",
  field: "",
  apps: {},
  working_day: null,
  steps: {},
  people: [],
});
export const email = ref("");
const waiting = [];

export const before = computed(() => [
  "you",
  "company",
  "language",
  "field",
  "companies",
  "apps",
  "plan",
  ...((offer.value?.regions || []).length > 1 ? ["region"] : []),
  "payment",
]);
export const after = computed(() => ["week", ...held.steps.map((one) => one.id), "people"]);
export const steps = computed(() => [...before.value, ...after.value]);

const ask = (method, params) => call(`${WIZARD}.${method}`, params);

function take(state) {
  if (!state) return;
  for (const key of Object.keys(held)) if (key in state) held[key] = state[key];
  for (const [key, value] of Object.entries(state.answers || {})) if (key in answers) answers[key] = value;
}

export function keep(request, key) {
  held.request = request;
  held.key = key;
  sessionStorage.setItem(KEPT, JSON.stringify({ request, key }));
  const url = new URL(window.location.href);
  url.searchParams.set("request", request);
  url.searchParams.set("key", key);
  window.history.replaceState(null, "", url);
}

export async function load(query) {
  offer.value = await ask("offer");
  const kept = query.request ? query : JSON.parse(sessionStorage.getItem(KEPT) || "{}");
  if (kept.request && kept.key) {
    try {
      take(await ask("resume", { request: kept.request, key: kept.key }));
      keep(kept.request, kept.key);
    } catch {
      sessionStorage.removeItem(KEPT);
      held.request = held.key = null;
    }
  }
  if (!answers.companies[0].name && query.name) answers.companies[0].name = String(query.name).slice(0, 140);
  if (!held.plan && query.plan) held.plan = query.plan;
}

export function note(step, event) {
  if (!held.request) return waiting.push({ step, event });
  ask("note", { request: held.request, key: held.key, step, event }).catch(() => {});
}

export function left(step) {
  if (!held.request || !navigator.sendBeacon) return;
  const form = new FormData();
  for (const [name, value] of Object.entries({ request: held.request, key: held.key, step, event: "Left", csrf_token: window.csrf_token })) form.append(name, value);
  navigator.sendBeacon(`/api/method/${WIZARD}.note`, form);
}

const zone = () => Intl.DateTimeFormat().resolvedOptions().timeZone;

export async function save(step, said = {}, events = []) {
  if (!held.request) {
    if (step !== "company") return waiting.push(...events);
    const state = await ask("start", {
      answers: { owner: answers.owner, companies: answers.companies },
      email: email.value || null,
      time_zone: zone(),
      events: [...waiting.splice(0), ...events],
    });
    keep(state.request, state.key);
    return take(state);
  }
  take(await ask("save", { request: held.request, key: held.key, step, ...said, events }));
}

export function chooseField(id) {
  answers.field = id;
  const preset = offer.value.fields.find((one) => one.id === id)?.apps || [];
  answers.apps = Object.fromEntries(offer.value.apps.filter((one) => !one.always).map((one) => [one.id, preset.includes(one.id)]));
}

export async function use(suggestion) {
  const given = suggestion.answers || {};
  if (suggestion.question === "field") {
    chooseField(given.field);
    return save("field", { answers: { field: answers.field, apps: answers.apps } });
  }
  if (suggestion.question === "apps") {
    answers.apps = { ...answers.apps, ...given.apps };
    return save("apps", { answers: { apps: answers.apps } });
  }
  if (suggestion.question === "plan") {
    held.plan = given.plan;
    return save("plan", { plan: held.plan });
  }
  if (suggestion.question === "region") {
    held.region = given.region;
    return save("region", { region: held.region });
  }
}

export const askGuide = (question, step, said) =>
  call("onedesk.one_admin.wizard_ask.ask", {
    question,
    step,
    said,
    answers: { field: answers.field, apps: answers.apps, language: answers.language, time_zone: answers.time_zone, plan: held.plan, region: held.region },
    request: held.request,
    key: held.key,
  });

export const pay = () => ask("pay", { request: held.request, key: held.key });

export const finish = (events) => ask("finish", { request: held.request, key: held.key, events });

export const free = (name) => call("onedesk.one_admin.signup.available", { name });
