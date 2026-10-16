<template>
  <!-- The apps the reader has let in (frappe's Third Party Apps), each taken
       away with frappe's own delete_client.
       Modelled on GitHub's Authorized OAuth Apps: a line an app, Revoke. -->
  <Head :title="__('Third Party Apps')" />
  <div class="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
    <Loading v-if="!list" />
    <List v-else-if="list.length" :columns="['minmax(0,1fr)', 'auto']" class="-mx-3 list-row-px-3">
      <ListRows :items="list" row-key="client" v-slot="{ item }">
        <ListRow>
          <ListCell class="flex-col !items-start gap-0.5 py-1.5">
            <span class="text-base text-ink-gray-8">{{ item.name }}</span>
            <span class="text-sm text-ink-gray-5">{{ __("Let in {0}", [item.since]) }}</span>
          </ListCell>
          <ListCell><Button theme="red" :label="__('Revoke')" @click="asked = item" /></ListCell>
        </ListRow>
      </ListRows>
    </List>
    <Empty v-else :title="__('No apps')" :line="__('Apps you let into your account will be here.')" />
    <Dialog :model-value="!!asked" :title="__('Revoke')" @update:model-value="asked = null">
      <template #default>
        <p class="text-p-base text-ink-gray-7">{{ __("Take away {0}'s access to your account?", [asked?.name]) }}</p>
      </template>
      <template #actions>
        <Button class="w-full" theme="red" variant="solid" :label="__('Revoke')" :loading="busy" @click="revoke" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Button, Dialog, toast } from "frappe-ui";
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list";

import { call } from "../call";
import Empty from "../parts/Empty.vue";
import Head from "../parts/Head.vue";
import Loading from "../parts/Loading.vue";
import { __ } from "../words";

const list = ref(null);
const asked = ref(null);
const busy = ref(false);
const load = async () => (list.value = await call("apps"));

async function revoke() {
  busy.value = true;
  try {
    await call("frappe.www.third_party_apps.delete_client", { client_id: asked.value.client });
    toast.success(__("Access taken away"));
    asked.value = null;
    load();
  } finally {
    busy.value = false;
  }
}

load();
</script>
