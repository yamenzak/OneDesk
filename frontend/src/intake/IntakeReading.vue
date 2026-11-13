<template>
  <div class="p-4 text-sm text-ink-gray-8">
    <div v-if="!reading" class="flex flex-col items-center gap-2 py-16 text-ink-gray-5">
      <span class="lucide-inbox size-6" aria-hidden="true" />
      <span class="text-base">{{ __("No document selected") }}</span>
    </div>
    <div v-else-if="missing" class="py-16 text-center text-base text-ink-gray-5">{{ __("Document not found") }}</div>
    <Loading v-else-if="!said" />
    <template v-else>
      <div class="text-lg font-semibold text-ink-gray-9">{{ said.title }}</div>
      <div class="mt-1 flex flex-wrap items-center gap-1 text-ink-gray-5">
        <span v-if="said.kind">{{ __(said.kind) }}</span>
        <span v-if="said.person">· {{ __("for {0}", [said.person]) }}</span>
        <template v-if="said.route">· <a :href="said.route" class="underline">{{ __("Open Document") }}</a></template>
      </div>
      <PlaceSpot :said="placed" class="mt-3" />
      <p v-if="said.summary" class="mt-3 text-ink-gray-7">{{ said.summary }}</p>

      <div class="mt-4 text-xs font-medium text-ink-gray-5">{{ __("What {0} did", [name("one_ai")]) }}</div>
      <ul class="mt-1 divide-y divide-outline-gray-1">
        <li v-if="!(said.actions || []).length" class="py-2 text-ink-gray-5">{{ __("Nothing") }}</li>
        <li v-for="act in said.actions || []" :key="act.name" class="py-2">
          <div class="flex flex-wrap items-center gap-2">
            <Badge v-if="chip(act)" :label="chip(act).label" :theme="chip(act).theme" size="sm" />
            <span class="min-w-0 flex-1">
              {{ act.said }}
              <template v-if="act.record">· <a :href="recordRoute(act.record[0], act.record[1])" class="underline">{{ __("Open") }}</a></template>
            </span>
            <span v-if="said.may_decide" class="flex gap-1">
              <template v-if="act.level === 'Proposed'">
                <Button size="sm" variant="solid" :label="__('Apply')" :disabled="busy" @click="settle(act, 1)" />
                <Button size="sm" :label="__('Dismiss')" :disabled="busy" @click="settle(act, 0)" />
              </template>
              <template v-else-if="act.level === 'Done'">
                <Button v-if="doubted(act)" size="sm" variant="solid" :label="__('Keep')" :disabled="busy" @click="keep(act)" />
                <Button size="sm" :label="__('Undo')" :disabled="busy" @click="undo(act)" />
              </template>
            </span>
          </div>
          <div v-for="(it, at) in act.change || []" :key="at" class="mt-1 text-ink-gray-7">
            {{ it.field }}: <s class="text-ink-gray-5">{{ String(it.from) }}</s> → {{ String(it.to) }}
          </div>
          <div v-for="(line, at) in whys(act)" :key="`why-${at}`" class="mt-1 text-ink-gray-5">{{ line }}</div>
        </li>
      </ul>

      <details class="mt-4">
        <summary class="cursor-pointer text-ink-gray-7">{{ __("All Details") }}</summary>
        <IntakeFacts :said="said" with-pay with-matter class="mt-3" />
        <IntakeExplain :said="said" class="mt-3" />
      </details>
    </template>
  </div>
</template>

<script setup>
// One document in Documents: what it is, what OneAI did with it and
// what waits for a decision, and everything read from it.
import { reactive, ref, watch } from "vue";
import { Badge, Button } from "frappe-ui";

import { Loading, PlaceSpot, __, alert, call, confirm, msgprint, onedesk, recordRoute, name } from "../kit";
import IntakeExplain from "./IntakeExplain.vue";
import IntakeFacts from "./IntakeFacts.vue";

const props = defineProps({ reading: { type: String, default: null } });
const emit = defineEmits(["changed"]);

const said = ref(null);
const missing = ref(false);
const busy = ref(false);
const placed = reactive({ notes: [], actions: [] });

async function load() {
  said.value = null;
  missing.value = false;
  if (!props.reading) return;
  const asked = props.reading;
  try {
    const got = await call("onedesk.one_ai.reading.inbox.item", { name: asked });
    if (asked !== props.reading) return;
    said.value = got;
    tell(got);
  } catch (e) {
    missing.value = true;
  }
}
watch(() => props.reading, load, { immediate: true });

const doubted = (act) => act.level === "Done" && act.audit === "Wrong";

function chip(act) {
  if (doubted(act)) return { label: __("Auditor Disagrees"), theme: "red" };
  if (act.level === "Proposed") return { label: __("Needs Review"), theme: "amber" };
  if (act.level === "Refused") return { label: __("Not allowed"), theme: "gray" };
  if (act.by_auditor) return { label: __("Auditor Approved"), theme: "green" };
  return null;
}

const whys = (act) =>
  [act.level !== "Done" ? act.why : "", doubted(act) || act.by_auditor || act.level === "Proposed" ? act.audit_why : ""].filter(Boolean);

async function again() {
  await load();
  emit("changed");
}

async function settle(act, take) {
  busy.value = true;
  await call("onedesk.one_ai.reading.act.settle", { action: act.name, take });
  busy.value = false;
  again();
}

async function keep(act) {
  busy.value = true;
  await call("onedesk.one_ai.reading.inbox.keep", { action: act.name });
  busy.value = false;
  again();
}

function undo(act) {
  confirm(__("Undo this?"), async () => {
    const done = await call("onedesk.one_ai.reading.act.undo_one", { action: act.name });
    if (done.why) msgprint(done.why);
    else alert(__("Undone"));
    again();
  });
}

// What the document is, for whatever else listens on this place
// (onedesk.places, "intake.reading").
function tell(got) {
  placed.notes = [];
  placed.actions = [];
  const places = onedesk().places;
  if (!places?.listening("intake.reading")) return;
  places.emit(
    "intake.reading",
    {
      name: got.name,
      title: got.title || "",
      kind: got.kind || "",
      person: got.person || "",
      summary: got.summary || "",
      route: got.route || "",
      actions: (got.actions || []).map((one) => ({ said: one.said, level: one.level, record: one.record || null })),
    },
    {
      note: (text, tone) => placed.notes.push({ text: String(text || ""), tone }),
      action: (label, handler) => placed.actions.push({ label: String(label || ""), handler }),
    }
  );
}
</script>
