<template>
  <Head :title="__('Your Data')" />
  <div class="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
    <Loading v-if="!state" />
    <div v-else class="flex flex-col gap-5">
      <Card :title="__('Copy of Your Data')" icon="lucide-file-down">
        <p v-if="copy && copy.status === 'Waiting'" class="mb-3 text-p-base text-ink-gray-6">{{ __("You requested a copy {0}. It's waiting for approval.", [copy.on]) }}</p>
        <p v-else-if="copy && copy.status === 'Gathering'" class="mb-3 text-p-base text-ink-gray-6">{{ __("Your copy is being prepared. You'll be notified when it's ready.") }}</p>
        <p v-else-if="copy && copy.ready" class="mb-3 text-p-base text-ink-gray-6">
          {{ __("Your copy from {0} is ready.", [copy.on]) }}<template v-if="copy.withheld"> {{ __("Withheld: {0}", [copy.withheld]) }}</template>
        </p>
        <p v-else class="mb-3 text-p-base text-ink-gray-6">{{ __("A file of everything this workspace holds about you, made after an administrator approves.") }}</p>
        <div class="flex flex-wrap gap-2">
          <Button v-if="copy && copy.ready" :label="__('Download My Data')" icon-left="lucide-download" :href="copy.url" download />
          <Button v-if="!asking" :label="copy && copy.ready ? __('Request New Copy') : __('Request My Data')" icon-left="lucide-file-down" :loading="busy" @click="ask" />
        </div>
      </Card>
      <Card :title="__('Delete Account')" icon="lucide-user-x">
        <p v-if="deletion && deletion.status === 'On Hold'" class="mb-3 text-p-base text-ink-gray-6">{{ __("Account deletion is on hold. {0}", [deletion.why || ""]) }}</p>
        <p v-else-if="deletion && deletion.status === 'Pending Verification'" class="mb-3 text-p-base text-ink-gray-6">{{ __("Check your email to confirm deleting your account.") }}</p>
        <p v-else-if="deletion" class="mb-3 text-p-base text-ink-gray-6">{{ __("You requested account deletion {0}. It's waiting for approval.", [deletion.on]) }}</p>
        <p v-else class="mb-3 text-p-base text-ink-gray-6">{{ __("Turn off your account and remove your name and address from the records the workspace keeps.") }}</p>
        <Button v-if="deletion" :label="__('Cancel Deletion')" icon-left="lucide-undo-2" :loading="busy" @click="withdraw" />
        <Button v-else theme="red" :label="__('Delete My Account')" icon-left="lucide-user-x" @click="asked = true" />
      </Card>
    </div>
    <Dialog v-model="asked" :title="__('Delete My Account')">
      <template #default>
        <div class="flex flex-col gap-3 text-p-base text-ink-gray-7">
          <p>{{ __("An administrator reviews the request. Then you're signed out and your account is turned off.") }} {{ __("Records the workspace keeps, such as invoices, stay without your name and address.") }}</p>
          <p>{{ __("This can't be undone. Request a copy of your data first if you need one.") }}</p>
          <FormControl v-if="state?.password" v-model="password" type="password" :label="__('Your Password')" required />
          <p v-else>{{ __("You'll get an email with a link to confirm.") }}</p>
        </div>
      </template>
      <template #actions>
        <Button class="w-full" theme="red" variant="solid" :label="__('Request Deletion')" :loading="busy" :disabled="state?.password && !password" @click="remove" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { Button, Dialog, FormControl, toast } from "frappe-ui";

import { call } from "../call";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import Card from "../parts/Card.vue";
import { realtime } from "../socket";
import { __ } from "../words";

const state = ref(null);
const busy = ref(false);
const asked = ref(false);
const password = ref("");

const copy = computed(() => state.value?.copy);
const deletion = computed(() => state.value?.deletion);
const asking = computed(() => copy.value && ["Waiting", "Gathering"].includes(copy.value.status));

const load = async () => (state.value = await call("your_data"));

async function act(method, args, said) {
  busy.value = true;
  try {
    await call(method, args);
    toast.success(said);
    await load();
    return true;
  } catch (error) {
    toast.error(error?.messages?.[0] || __("That didn't go through. Try again in a moment."));
    return false;
  } finally {
    busy.value = false;
  }
}

const ask = () => act("onedesk.one.privacy_copy.ask", {}, __("Requested. You'll be notified when it's ready."));
const withdraw = () => act("onedesk.one.privacy.withdraw", {}, __("Deletion cancelled"));
async function remove() {
  const said = state.value.password ? __("Requested. You'll be notified of the decision.") : __("Check your email to confirm.");
  if (await act("onedesk.one.privacy.ask_to_delete", { password: password.value }, said)) {
    asked.value = false;
    password.value = "";
  }
}

const socket = realtime();
socket.on("one_privacy", load);
onBeforeUnmount(() => socket.off("one_privacy", load));
load();
</script>
