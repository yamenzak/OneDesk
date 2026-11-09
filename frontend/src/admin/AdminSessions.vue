<template>
  <Page>
    <Loading v-if="!said" />
    <div v-else class="mt-6">
      <div v-if="!said.can_start && !said.sessions.length" class="rounded-3 bg-surface-gray-1 p-4 text-base text-ink-gray-6">
        {{ __("No server is connected yet. Connect one under Servers.") }}
      </div>
      <Rows v-else :rows="rows" :empty="__('No sessions yet')" />
    </div>

    <Dialog v-model:open="starting" :title="__('New Session')" size="lg">
      <div class="space-y-4">
        <div class="grid gap-2 sm:grid-cols-3">
          <button
            v-for="one in sources"
            :key="one.value"
            type="button"
            class="rounded-3 border p-3 text-start"
            :class="form.source === one.value ? 'border-outline-gray-4 bg-surface-gray-2' : 'border-outline-gray-2'"
            @click="form.source = one.value"
          >
            <div class="text-base font-medium text-ink-gray-8">{{ one.label }}</div>
            <div class="mt-1 text-sm text-ink-gray-5">{{ one.about }}</div>
          </button>
        </div>
        <FormControl v-model="form.title" type="text" :label="__('Name')" :placeholder="__('Name')" />
        <FormControl v-if="form.source === COPY" v-model="form.tenant" type="select" :label="__('Workspace')" :options="workspaces" :description="workspaces.length ? '' : __('No workspace has turned on Training Copies.')" />
        <FormControl v-model="form.lasts" type="select" :label="__('Expires After')" :options="lasts" />
      </div>
      <template #actions>
        <div class="flex justify-end">
          <Button variant="solid" :label="__('Start Session')" :loading="busy" :disabled="!ready" @click="begin" />
        </div>
      </template>
    </Dialog>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Button, Dialog, FormControl } from "frappe-ui";

import { Loading, Page, Rows, __, alert, call, followList, get, goTo, onedesk, openTab } from "../kit";

const props = defineProps({ onTitle: Function, onActions: Function });

const COPY = "Workspace Copy";
const THEMES = { Starting: "blue", Running: "green", Stopped: "gray", Deleting: "amber", Failed: "red" };

const said = ref(null);
const starting = ref(false);
const busy = ref(false);
const form = reactive({ title: "", source: "Fresh", tenant: "", lasts: "1 Day" });

const load = async () => {
  said.value = await get("onedesk.one_admin.sessions.board");
  props.onTitle?.({ title: __("Sessions") });
  props.onActions?.(said.value.can_start ? [{ label: __("New Session"), primary: true, onClick: () => (starting.value = true) }] : []);
};
load();
const stops = ["Workspace Session", "Workspace Server", "Tenant"].map((doctype) => followList(doctype, load));
onBeforeUnmount(() => stops.forEach((stop) => stop()));

const sources = computed(() => [
  { value: "Fresh", label: __("Fresh"), about: __("A new, empty workspace.") },
  { value: "Demo Data", label: __("Demo Data"), about: __("A year of a demo company.") },
  { value: COPY, label: __("Workspace Copy"), about: __("A workspace's newest database backup.") },
]);
const workspaces = computed(() => [{ label: "", value: "" }, ...(said.value?.workspaces || []).map((one) => ({ label: one.workspace_name || one.name, value: one.name }))]);
const lasts = computed(() => (said.value?.lasts || []).map((one) => ({ label: __(one), value: one })));
const ready = computed(() => form.source !== COPY || form.tenant);
watch(starting, (on) => on && Object.assign(form, { title: "", source: "Fresh", tenant: "", lasts: "1 Day" }));

async function begin() {
  busy.value = true;
  try {
    await call("onedesk.one_admin.sessions.start", { title: form.title, source: form.source, lasts: form.lasts, tenant: form.tenant });
    starting.value = false;
    alert(__("Session started."));
    await load();
  } finally {
    busy.value = false;
  }
}

const expires = (hours) => (hours >= 24 ? __("Expires in {0} days", [Math.round(hours / 24)]) : __("Expires in {0} hours", [hours]));
const open = async (one) => openTab((await call("onedesk.one_admin.sessions.sign_in", { name: one.name })).url);
const act = (method, one, done) => () => call(`onedesk.one_admin.sessions.${method}`, { name: one.name }).then(() => (alert(done), load()));

async function remove(one) {
  const go = await onedesk().interface.ask({ question: __("Delete {0}?", [one.title]), effect: __("Everything in it goes with it."), verb: __("Delete Session") });
  if (go) act("delete", one, __("Session deleted."))();
}

const rows = computed(() =>
  said.value.sessions.map((one) => ({
    key: one.name,
    label: one.title,
    below: one.status === "Failed" ? one.error : one.link,
    sub: __(one.source),
    badge: { label: __(one.status), theme: THEMES[one.status] || "gray" },
    dim: one.status === "Deleting" ? "" : expires(one.expires_in_hours),
    onClick: () => goTo("Form", "Workspace Session", one.name),
    actions: [
      one.status === "Running" && { label: __("Open"), onClick: () => open(one) },
      one.status === "Running" && { label: __("Stop"), onClick: act("stop", one, __("Session stopped.")) },
      one.status === "Stopped" && { label: __("Start"), onClick: act("resume", one, __("Session started.")) },
      !["Deleting"].includes(one.status) && { label: __("Delete"), onClick: () => remove(one) },
    ].filter(Boolean),
  }))
);
</script>
